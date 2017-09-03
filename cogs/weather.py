# -*- coding: utf-8 -*-

from discord.ext import commands
import discord
from lxml import html
import aiohttp
import re
from cogs.cog import Cog

async def get_data(url) -> str:
    async with aiohttp.ClientSession() as session:
        weewx_req = await session.get(url)
        weewx = await weewx_req.text()
        return weewx


class Weather(Cog):
    """Lets you access the alext.duckdns.org/weewx/{,c/} weather station from discord"""

    @commands.command()
    async def weather(self, ctx, unit="c"):
        if unit.lower() not in set("fck"):
            return await ctx.send("you idiot i only take f, c, or k for units.")
        if unit.lower() == "f":
            url = "http://alext.duckdns.org/weewx/"
        else:
            url = "http://alext.duckdns.org/weewx/c"
        data = html.fromstring(await get_data(url))

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

        if "N/A" in wind:
            msg = f"Weather at Alex's Home:\nTemp: {temp}\nInside Tempature: {in_temp}"
        else:
            msg = f"Weather at Alex's Home:\nTemp: {temp}\nWind speed: {wind}\nInside Tempature: {in_temp}"

        await ctx.send(msg)

def setup(bot):
    bot.add_cog(Weather(bot))
