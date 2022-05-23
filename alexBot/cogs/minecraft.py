import logging
import re

import discord
import mcstatus
from discord.ext import commands

from ..tools import Cog, get_json

log = logging.getLogger(__name__)

REMOVE_SECTION = re.compile("(\U000000a7.)")


class Minecraft(Cog):
    @commands.command()
    async def mcStatus(self, ctx: commands.Context, *, server: str = None):
        # a!mcStatus
        # -> guild.Minecraft
        if server is None and ctx.guild is not None:
            gd = await self.bot.db.get_guild_data(ctx.guild.id)
            server = gd.config.minecraft if gd.config.minecraft else None
            if server is None:
                return await ctx.send(
                    "please provide a server via argument or with `config set guild.Minecraft <SERVER>`"
                )
        try:

            mcserver = mcstatus.MinecraftServer.lookup(server)
            status = await mcserver.async_status()
        except Exception:
            return await ctx.send("an error occured, the server may be down..")

        embed = discord.Embed(description=REMOVE_SECTION.sub('', status.description['text']))

        embed.title = f"{mcserver.host}:{mcserver.port}"

        if status.players.sample:
            embed.add_field(name="players", value='\n'.join([player.name for player in status.players.sample]))
        embed.add_field(name="Online / Max", value=f"{status.players.online} / {status.players.max}")

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Minecraft(bot))
