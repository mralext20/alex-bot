# -*- coding: utf-8 -*-

import logging
import re
import time
import urllib.parse
from datetime import datetime

import aiohttp
import discord
import humanize
from discord.ext import commands
from lxml import html

from ..tools import Cog
from ..tools import get_json
from ..tools import get_text

log = logging.getLogger(__name__)

class Weather(Cog):
    @commands.command()
    async def weather(self, ctx, unit="c"):
        """Lets you access the alext.duckdns.org/weewx/{,c/} weather station from discord"""
        if unit.lower() not in set("fck"):
            raise commands.BadArgument("the only units i understand are [F, K, C].")
        if unit.lower() == "f":
            url = "http://alext.duckdns.org/weewx"
        else:
            url = "http://alext.duckdns.org/weewx/c"
        data = html.fromstring(await get_text(self.bot.session, url))

        temp = data.xpath('//*[@id="stats_group"]/div[1]/table/tbody/tr[1]/td[2]/text()')[0]
        wind = data.xpath('//*[@id="stats_group"]/div[1]/table/tbody/tr[8]/td[2]/text()')[0]
        in_temp = data.xpath('//*[@id="stats_group"]/div[1]/table/tbody/tr[10]/td[2]/text()')[0]

        if unit.lower() == "k":
            # add 237.15 to C to get kelvin for some WEIRDO
            rec = re.compile("-?([\d.])")
            temp = int(rec.search(temp).group(0))
            temp = f"{temp+237.15}k"
            in_temp = int(rec.search(in_temp).group(0))
            in_temp = f"{in_temp+237.15}k"
            # set the URL to none to prevent getting a graph for K that doesnt exist.
            url = None

        if "N/A" in wind:
            msg = f"Weather at Alex's Home:\nTemp: {temp}\nInside Tempature: {in_temp}"
        else:
            msg = f"Weather at Alex's Home:\nTemp: {temp}\nWind speed: {wind}\nInside Tempature: {in_temp}"

        if url is not None:
            embed = discord.Embed()
            embed.set_image(url=f"{url}/daytempdew.png?t={int(time.time()/300)}")
            await ctx.send(msg, embed=embed)
        else:
            await ctx.send(msg)

    @commands.command()
    async def metar(self, ctx: commands.Context, arg1: str, *, arg2: str=None):
        """
        if only one arg is given, that station's metar is returned.
        if two args are uses, the first must be one of raw, readable, metar, or metar-readable.
        the metar type requires a metar to be put after the argument.
        """
        await ctx.trigger_typing()
        if arg2 is None:
            station = arg1
            display_type = 'normal'
        else:
            station = arg2
            try:
                assert station is not None
            except AssertionError:
                await ctx.send('you need to provide a station...')
            try:
                assert arg1.lower() in ['raw', 'readable', 'metar', 'metar-readable']
            except AssertionError:
                return await ctx.send("arg1 must be one of raw, readable, metar, metar-readable,"
                                      "otherwise provide just the station")
            display_type = arg1.lower()
        station = station.upper()

        if 'metar' in display_type:
            try:
                data = await get_json(self.bot.session, f'https://avwx.rest/api/parse/metar?report='
                                                        f'{urllib.parse.quote(station)}'
                                                        f'&options=info,speech,translate')
            except aiohttp.ClientResponseError:
                return await ctx.send(f"something happened. try again?")
        else:
            try:
                data = await get_json(self.bot.session, f'https://avwx.rest/api/metar/{station}'
                                                        f'?options=info,speech,translate')
            except aiohttp.ClientResponseError:
                return await ctx.send(f"something happened. try again?")

        if 'Error' in data:
            raise commands.errors.BadArgument(data['Error'])

        # handle raw and readable types
        if display_type == 'raw':
            return await ctx.send(data['Raw-Report'])
        elif 'readable' in display_type:
            return await ctx.send(data['Speech'])

        embed = discord.Embed()

        if 'metar' not in display_type:
            now = datetime.utcnow()
            report_time = datetime.strptime(data['Time'], "%d%H%MZ")
            report_time = report_time.replace(year=now.year, month=now.month)  # this will fail around end of month/year
            embed.set_footer(text=f"report {humanize.naturaldelta(report_time-now)} old, "
                                  f"please only use this data for planning purposes.")

        color = data['Flight-Rules']

        if color == "VFR":
            color = discord.Color.green()
        elif color == "MVFR":
            color = discord.Color.blue()
        elif color == "IFR":
            color = discord.Color.red()
        elif color == "LIFR":
            color = discord.Color.magenta()
        else:
            color = discord.Color.default()

        embed.colour = color
        info = data['Info']
        try:
            if info['City'] == '':
                city = None
            else:
                city = info['City']

            if info['State'] == '':
                state = None
            else:
                state = info['State']

            if info['Country'] == '':
                country = None
            else:
                country = info['Country']
        except KeyError:
            city = None
            state = None
            country = None
        try:
            if info['Name'] == '':
                embed.title = station
            else:
                embed.title = info['Name']
        except KeyError:
            embed.title = station

        if city is not None:
            embed.title += f", {city}"
        if state is not None:
            embed.title += f", {state}"
        if country is not None:
            embed.title += f", {country}"

        embed.title = f"{embed.title} ({station.split()[0]})"
        if 'metar' in display_type:
            embed.add_field(name="Raw", value=station)
        else:
            embed.add_field(name="Raw", value=data['Raw-Report'])
        embed.add_field(name="Readable", value=data['Speech'])

        if data['Translations']['Clouds'] != "":
            embed.add_field(name="Clouds", value=data['Translations']['Clouds'])

        if data['Translations']['Wind'] != "":
            embed.add_field(name="Wind", value=data['Translations']['Wind'])

        if data['Translations']['Altimeter'] != "":
            embed.add_field(name="Altimeter", value=data['Translations']['Altimeter'], inline=True)

        if data['Translations']['Temperature'] != "":
            embed.add_field(name="Temperature", value=data['Translations']['Temperature'], inline=True)

        if data['Flight-Rules'] != "":
            embed.add_field(name="Flight Rule", value=data['Flight-Rules'], inline=True)

        if data['Translations']['Visibility'] != "":
            embed.add_field(name="Visibility", value=data['Translations']['Visibility'], inline=True)

        if 'metar' not in display_type:
            embed.timestamp = report_time
        if display_type is None:
            await ctx.send("Check out new readable and raw only displays! see a!help metar for details,"
                           " or join my server (a!about) and ask for help there.", embed=embed)
        else:
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Weather(bot))
