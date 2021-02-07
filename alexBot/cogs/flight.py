from datetime import datetime, timezone

import logging

import aiohttp
import discord
import humanize
from discord.ext import commands

from alexBot.tools import Cog, get_json, get_xml

log = logging.getLogger(__name__)


class Flight(Cog):
    @commands.command()
    async def metar(self, ctx: commands.Context, *, stations):
        """
        returns the METAR for a given station or set of stations. also works with cord pairs (40.38,-73.46)
        """
        await ctx.trigger_typing()

        station = stations.upper()

        try:
            data = await get_json(
                self.bot.session,
                f'https://avwx.rest/api/metar/{station}'
                f'?options=info,speech,translate'
                f'&onfail=cache'
                f'&token={self.bot.config.avwx_token}',
            )
            if data is None:
                raise commands.BadArgument('It Appears that station doesnt have METAR data available.')
        except aiohttp.ClientResponseError:
            return await ctx.send("something happened. try again?")
        if 'meta' in data or 'Meta' in data:
            try:
                log.info(data['meta'])
            except KeyError:
                pass
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
        try:
            report_time = datetime.strptime(data['time']['dt'], "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            report_time = datetime.strptime(data['time']['dt'].replace(':00Z', '00Z'), "%Y-%m-%dT%H:%M:%S%zZ")

            now = datetime.now(tz=timezone.utc)
        embed.set_footer(
            text=f"report {humanize.naturaldelta(report_time - now)} old, "
            f"please only use this data for planning purposes."
        )

        info = data['info']
        magdec = ""
        if data['wind_direction']['value'] is not None and self.bot.config.government_is_working:
            magdec = await get_xml(
                ctx.bot.session,
                f"https://www.ngdc.noaa.gov/geomag-web/calculators/calculateDeclination"
                f"?lat1={info['latitude']}&lon1={info['longitude']}&resultFormat=xml",
            )
            try:
                magdec = float(magdec['maggridresult']['result']['declination']['#text'])
            except KeyError:
                log.error(f'magdec failed, value was {magdec}')
                magdec = 0

            magdec = magdec + int(data['wind_direction']['value'])  # add the magdec to the direction of the wind
            if magdec > 360:  # if the declaration ends up being more than 360, subtract the extra.
                magdec = magdec - 360
            elif magdec < 0:  # same as above, but for less than 0 condition.
                magdec = magdec + 360

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

        embed.add_field(name="Raw", value=data['raw'], inline=False)
        embed.add_field(name="Readable", value=data['speech'], inline=False)
        translations = data['translate']
        translations['clouds'] = translations['clouds'].replace(', ', '\n')
        if translations['clouds'] != "":
            embed.add_field(name="Clouds", value=translations['clouds'], inline=False)

        if translations['wind'] != "":
            if magdec != "":
                if data['wind_gust'] is not None:
                    embed.add_field(
                        name="Wind",
                        value=f"{data['wind_direction']['repr']}@{data['wind_speed']['repr']}"
                        f"G{data['wind_gust']['repr']}(True)\n"
                        f""
                        f"{magdec:0f}@{data['wind_speed']['repr']}"
                        f"G{data['wind_gust']['repr']}"
                        f" (with Variation",
                    )
                else:
                    embed.add_field(
                        name="Wind",
                        value=f"{data['wind_direction']['repr']}@"
                        f"{data['wind_speed']['repr']} (True)\n "
                        f"{magdec:.0f}@"
                        f"{data['wind_speed']['repr']} (with variation)",
                    )
            else:
                embed.add_field(name="Wind", value=translations['wind'], inline=False)

        if translations['altimeter'] != "":
            embed.add_field(name="Altimeter", value=translations['altimeter'], inline=False)

        if translations['temperature'] != "":
            embed.add_field(name="Temperature", value=translations['temperature'], inline=False)

        if data['flight_rules'] != "":
            embed.add_field(name="Flight Rule", value=data['flight_rules'], inline=False)

        if translations['visibility'] != "":
            embed.add_field(name="Visibility", value=translations['visibility'], inline=False)

        embed.timestamp = report_time
        if color == discord.Color.red() or color == discord.Color.magenta():
            await ctx.send('you might want to reconsider flying.', embed=embed)
        else:
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Flight(bot))
