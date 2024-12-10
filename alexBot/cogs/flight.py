import logging
from datetime import datetime, timezone

import avwx
import discord
import geomag
import humanize
from avwx.exceptions import BadStation
from discord import app_commands
from discord.ext import commands

from alexBot.tools import Cog

log = logging.getLogger(__name__)


class Flight(Cog):
    wmm = geomag.WorldMagneticModel()

    flightrule_color = {
        "VFR": discord.Color.green(),
        "MVFR": discord.Color.blue(),
        "IFR": discord.Color.red(),
        "LIFR": discord.Color.magenta(),
    }

    @app_commands.command(name="metar")
    async def metar(self, interaction: discord.Interaction, station: str):
        """
        returns the METAR for a given station.
        """
        await interaction.response.defer(thinking=True)
        station = station.upper()
        try:
            location = avwx.Station.from_icao(station)
        except BadStation:
            try:
                location = avwx.Station.from_iata(station)
            except BadStation as e:
                raise commands.BadArgument(*e.args)
        if not location.icao:
            return await interaction.followup.send("could not find that station")
        metar = avwx.Metar(location.icao)

        if not await metar.async_update():
            return await interaction.followup.send(f"can not retrive metar data for {location.name}")

        embed = discord.Embed(color=self.flightrule_color.get(metar.data.flight_rules, discord.Color.default()))

        now = datetime.now(tz=timezone.utc)
        embed.set_footer(
            text=f"report {humanize.naturaldelta(metar.data.time.dt - now)} old, "
            f"please only use this data for planning purposes."
        )

        magdec = self._compute_magdec(location, metar)

        embed.title = f"{location.name}, {location.country} ({location.icao})"

        embed.add_field(name="Raw", value=metar.data.raw, inline=False)
        embed.add_field(name="Spoken", value=metar.speech, inline=False)
        translations = metar.translations

        if translations.clouds != "":
            embed.add_field(name="Clouds", value=translations.clouds, inline=False)

        self._handle_wind(metar, embed, magdec, translations)

        if translations.altimeter != "":
            embed.add_field(name="Altimeter", value=translations.altimeter, inline=False)

        if translations.temperature != "":
            embed.add_field(name="Temperature", value=translations.temperature, inline=False)

        embed.add_field(name="Flight Rule", value=metar.data.flight_rules, inline=False)

        if translations.visibility != "":
            embed.add_field(name="Visibility", value=translations.visibility, inline=False)

        embed.timestamp = metar.data.time.dt
        if metar.data.flight_rules in ["LIFR", "IFR"]:
            await interaction.followup.send('you might want to reconsider flying.', embed=embed)
        else:
            await interaction.followup.send(embed=embed)

    def _handle_wind(self, metar, embed, magdec, translations):
        if translations.wind is not None:
            if magdec is not None:
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

    def _compute_magdec(self, location, metar):
        magdec = None
        if metar.data.wind_direction.value is not None:
            declination = self.wmm.calc_mag_field(
                location.latitude, location.longitude, location.elevation_ft
            ).declination

            magdec = declination + int(metar.data.wind_direction.value)  # add the magdec to the direction of the wind
            if magdec > 360:  # if the declaration ends up being more than 360, subtract the extra.
                magdec = magdec - 360
            elif magdec < 0:  # same as above, but for less than 0 condition.
                magdec = magdec + 360
        return magdec

    @app_commands.command(name="taf")
    async def taf(self, interaction: discord.Interaction, station: str):
        """
        returns the METAR for a given station.
        """
        await interaction.response.defer(thinking=True)
        station = station.upper()
        try:
            location = avwx.Station.from_icao(station)
        except BadStation:
            try:
                location = avwx.Station.from_iata(station)
            except BadStation as e:
                raise commands.BadArgument(*e.args)

        taf = avwx.Taf(location.icao)
        if not await taf.async_update():
            return await interaction.followup.send(f"cannot get TAF for {location.name}")

        embed = discord.Embed()

        now = datetime.now(tz=timezone.utc)

        embed.timestamp = taf.data.time.dt
        embed.title = f"{location.name}, {location.country} ({location.icao})"

        embed.set_footer(
            text=f"report {humanize.naturaldelta(taf.data.time.dt - now)} old, "
            f"please only use this data for planning purposes."
        )

        embed.add_field(name="Raw", value=taf.data.sanitized)
        embed.add_field(name="Spoken", value=taf.speech)
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Flight(bot))
