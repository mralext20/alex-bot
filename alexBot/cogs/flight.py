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
        report_time = datetime.strptime(data['Time'], "%d%H%MZ")
        report_time = report_time.replace(year=now.year, month=now.month)  # this will fail around end of month/year
        embed.set_footer(text=f"report {humanize.naturaldelta(report_time - now)} old, "
        f"please only use this data for planning purposes.")

        info = data['Info']
        magdec = ""
        if data['Wind-Direction'] not in ['VRB', ''] and self.bot.config.government_is_working:
            try:
                magdec = await get_xml(ctx.bot.session,
                                       f"https://www.ngdc.noaa.gov/geomag-web/calculators/calculateDeclination"
                                       f"?lat1={info['Latitude']}&lon1={info['Longitude']}&resultFormat=xml")

                magdec = float(magdec['maggridresult']['result']['declination']['#text'])

                magdec = magdec + int(data['Wind-Direction'])  # add the magdec to the direction of the wind
                if magdec > 360:  # if the declaration ends up being more than 360, subtract the extra.
                    magdec = magdec - 360
                elif magdec < 0:  # same as above, but for less than 0 condition.
                    magdec = magdec + 360
            except KeyError:
                magdec = ""

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

        embed.add_field(name="Raw", value=data['Raw-Report'])
        embed.add_field(name="Readable", value=data['Speech'])
        translations = data['Translate']
        if translations['Cloud-List'] != "":
            embed.add_field(name="Clouds", value=translations['Cloud-List'])

        if translations['Wind'] != "":
            if magdec != "":
                if data['Wind-Gust'] is not '':
                    embed.add_field(name="Wind", value=f"{data['Wind-Direction']}@{data['Wind-Speed']}"
                    f"G{data['Wind-Gust']}"
                    f"(True) {magdec:0f}@{data['Wind-Speed']}G{data['Wind-Gust']}"
                    f" (with Variation")
                else:
                    embed.add_field(name="Wind", value=f"{data['Wind-Direction']}@{data['Wind-Speed']} (True) "
                    f"{magdec:.0f}@{data['Wind-Speed']} (with variation)")
            else:
                embed.add_field(name="Wind", value=translations['Wind'])

        if translations['Altimeter'] != "":
            embed.add_field(name="Altimeter", value=translations['Altimeter'], inline=True)

        if translations['Temperature'] != "":
            embed.add_field(name="Temperature", value=translations['Temperature'], inline=True)

        if data['Flight-Rules'] != "":
            embed.add_field(name="Flight Rule", value=data['Flight-Rules'], inline=True)

        if translations['Visibility'] != "":
            embed.add_field(name="Visibility", value=translations['Visibility'], inline=True)

        embed.timestamp = report_time
        if color == discord.Color.red() or color == discord.Color.magenta():
            await ctx.send('you might want to reconsider flying.', embed=embed)
        else:
            await ctx.send(embed=embed)




def setup(bot):
    bot.add_cog(Flight(bot))
