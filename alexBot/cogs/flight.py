import logging
from datetime import datetime, timezone

import avwx
import discord
import geomag
import humanize
from avwx.exceptions import BadStation
from discord.ext import commands

from alexBot.tools import Cog, get_json, get_xml

log = logging.getLogger(__name__)


class Flight(Cog):

    flightrule_color = {
        "VFR": discord.Color.green(),
        "MVFR": discord.Color.blue(),
        "IFR": discord.Color.red(),
        "LIFR": discord.Color.magenta(),
    }

    @commands.command()
    async def metar(self, ctx: commands.Context, station: str):
        """
        returns the METAR for a given station.
        """
        await ctx.trigger_typing()
        station = station.upper()
        try:
            metar = avwx.Metar(station)
        except BadStation as e:
            raise commands.errors.BadArgument(*e.args)

        await metar.async_update()

        embed = discord.Embed(color=self.flightrule_color.get(metar.data.flight_rules, discord.Color.default()))

        now = datetime.utcnow()

        now = datetime.now(tz=timezone.utc)
        embed.set_footer(
            text=f"report {humanize.naturaldelta(metar.data.time.dt - now)} old, "
            f"please only use this data for planning purposes."
        )

        magdec = None
        if metar.data.wind_direction.value is not None:
            declination = geomag.declination(
                metar.station.latitude, metar.station.longitude, metar.station.elevation_ft
            )

            magdec = declination + int(metar.data.wind_direction.value)  # add the magdec to the direction of the wind
            if magdec > 360:  # if the declaration ends up being more than 360, subtract the extra.
                magdec = magdec - 360
            elif magdec < 0:  # same as above, but for less than 0 condition.
                magdec = magdec + 360

        location = ""
        if metar.station.city != "":
            location += f", {metar.station.city}"
        if metar.station.state != "":
            location += f", {metar.station.state}"
        if metar.station.country != "":
            location += f", {metar.station.country}"

        embed.title = f"{metar.station.name}, {location} ({metar.station.icao})"

        embed.add_field(name="Raw", value=metar.data.raw, inline=False)
        embed.add_field(name="Spoken", value=metar.speech, inline=False)
        translations = metar.translations

        if translations.clouds != "":
            embed.add_field(name="Clouds", value=translations.clouds, inline=False)

        if translations.wind != "":
            if magdec != "":
                if metar.data.wind_gust is not None:
                    embed.add_field(
                        name="Wind",
                        value=f"{metar.data.wind_direction.repr}@{metar.data.wind_speed.repr}"
                        f"G{metar.data.wind_gust.repr} (True)\n"
                        f""
                        f"{magdec:1f}@{metar.data.wind_speed.repr}"
                        f"G{metar.data.wind_gust.repr} (with variation)",
                    )
                else:
                    embed.add_field(
                        name="Wind",
                        value=f"{metar.data.wind_direction.repr}@"
                        f"{metar.data.wind_speed.repr} (True)\n "
                        f"{magdec:.1f}@"
                        f"{metar.data.wind_speed.repr} (with variation)",
                    )
            else:
                embed.add_field(name="Wind", value=translations.wind, inline=False)

        if translations.altimeter != "":
            embed.add_field(name="Altimeter", value=translations.altimeter, inline=False)

        if translations.temperature != "":
            embed.add_field(name="Temperature", value=translations.temperature, inline=False)

        embed.add_field(name="Flight Rule", value=metar.data.flight_rules, inline=False)

        if translations.visibility != "":
            embed.add_field(name="Visibility", value=translations.visibility, inline=False)

        embed.timestamp = metar.data.time.dt
        if embed.color == discord.Color.red() or embed.color == discord.Color.magenta():
            await ctx.send('you might want to reconsider flying.', embed=embed)
        else:
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Flight(bot))
