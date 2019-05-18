from datetime import datetime

import aiohttp
import discord
import humanize
from discord.ext import commands

from alexBot.tools import Cog, get_json, get_xml


class Flight(Cog):
    @commands.command()
    async def metar(self, ctx: commands.Context, *, stations):
        """
        returns the METAR for a given station or set of stations. also works with cord pairs (40.38,-73.46)
        """
        await ctx.trigger_typing()

        station = stations.upper()

        try:
            data = await get_json(self.bot.session, f'https://avwx.rest/api/metar/{station}'
            f'?options=info,speech,translate'
            f'&onfail=cache')
            if data is None:
                raise commands.BadArgument('It Appears that station doesnt have METAR data available.')
        except aiohttp.ClientResponseError:
            return await ctx.send(f"something happened. try again?")

        if 'error' in data or 'Error' in data:
            try:
                e = data['help']
            except KeyError:
                try:
                    e = data['Help']
                except KeyError:
                    try:
                        e = data['error']
                    except KeyError:
                        e = data['Error']

            raise commands.errors.BadArgument(e)

        embed = discord.Embed()

        now = datetime.utcnow()
        report_time = datetime.strptime(data['time']['dt'], "%Y-%m-%dT%H:%M:%SZ")
        report_time = report_time.replace(year=now.year, month=now.month)  # this will fail around end of month/year
        embed.set_footer(text=f"report {humanize.naturaldelta(report_time - now)} old, "
        f"please only use this data for planning purposes.")

        info = data['info']
        magdec = ""
        if data['wind_direction'] not in ['VRB', ''] and self.bot.config.government_is_working:
            try:
                magdec = await get_xml(ctx.bot.session,
                                       f"https://www.ngdc.noaa.gov/geomag-web/calculators/calculateDeclination"
                                       f"?lat1={info['Latitude']}&lon1={info['Longitude']}&resultFormat=xml")

                magdec = float(magdec['maggridresult']['result']['declination']['#text'])

                magdec = magdec + int(data['wind_direction'])  # add the magdec to the direction of the wind
                if magdec > 360:  # if the declaration ends up being more than 360, subtract the extra.
                    magdec = magdec - 360
                elif magdec < 0:  # same as above, but for less than 0 condition.
                    magdec = magdec + 360
            except KeyError:
                magdec = ""

        color = data['flight_rules']
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

        try:
            if info['city'] == '':
                city = None
            else:
                city = info['city']

            if info['state'] == '':
                state = None
            else:
                state = info['state']

            if info['country'] == '':
                country = None
            else:
                country = info['country']
        except KeyError:
            city = None
            state = None
            country = None
        try:
            if info['Name'] == '':
                embed.title = station
            else:
                embed.title = info['name']
        except KeyError:
            embed.title = station

        if city is not None:
            embed.title += f", {city}"
        if state is not None:
            embed.title += f", {state}"
        if country is not None:
            embed.title += f", {country}"

        embed.title = f"{embed.title} ({station.split()[0]})"

        embed.add_field(name="Raw", value=data['raw'])
        embed.add_field(name="Readable", value=data['speech'])
        translations = data['translate']
        if translations['clouds'] != "":
            embed.add_field(name="Clouds", value=translations['clouds'])

        if translations['wind'] != "":
            if magdec != "":
                if data['wind_gust'] is not '':
                    embed.add_field(name="Wind", value=f"{data['wind_direction']}@{data['wind_seed']}"
                    f"G{data['wind_gust']}"
                    f"(True) {magdec:0f}@{data['wind_speed']}G{data['wind_gust']}"
                    f" (with Variation")
                else:
                    embed.add_field(name="Wind", value=f"{data['wind_direction']}@{data['wind_speed']} (True) "
                    f"{magdec:.0f}@{data['wind_speed']} (with variation)")
            else:
                embed.add_field(name="Wind", value=translations['wind'])

        if translations['altimeter'] != "":
            embed.add_field(name="Altimeter", value=translations['altimeter'], inline=True)

        if translations['temperature'] != "":
            embed.add_field(name="Temperature", value=translations['temperature'], inline=True)

        if data['flight_rules'] != "":
            embed.add_field(name="Flight Rule", value=data['flight_rules'], inline=True)

        if translations['visibility'] != "":
            embed.add_field(name="Visibility", value=translations['visibility'], inline=True)

        embed.timestamp = report_time
        if color == discord.Color.red() or color == discord.Color.magenta():
            await ctx.send('you might want to reconsider flying.', embed=embed)
        else:
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Flight(bot))
