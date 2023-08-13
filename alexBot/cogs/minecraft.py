import logging
import re
from typing import Optional

import discord
import mcstatus
from discord import app_commands
from sqlalchemy import select

from alexBot import database as db

from ..tools import Cog

log = logging.getLogger(__name__)

REMOVE_SECTION = re.compile("(\U000000a7.)")


class Minecraft(Cog):
    @app_commands.command(name="mc-status", description="get the status of a minecraft server")
    async def mcStatus(self, interaction: discord.Interaction, server: Optional[str] = None):
        if server is None and interaction.guild is not None:
            #  retrive server from database if not provided
            async with db.async_session() as session:
                if cfg := await session.scalar(
                    select(db.GuildConfig).where(db.GuildConfig.guildId == interaction.guild.id)
                ):
                    server = cfg.minecraft if cfg.minecraft else None

        if server is None:
            return await interaction.response.send_message(
                "please provide a server via argument or with `config set guild.Minecraft <SERVER>`",
                ephemeral=True,
            )

        await interaction.response.defer(thinking=True)
        try:
            mcserver = mcstatus.MinecraftServer.lookup(server)
            status = await mcserver.async_status()
        except:
            return await interaction.followup.send("an error occured, the server may be down..")

        embed = discord.Embed(description=REMOVE_SECTION.sub('', status.description['text']))

        embed.title = f"{mcserver.host}:{mcserver.port}"

        if status.players.sample:
            embed.add_field(name="players", value='\n'.join([player.name for player in status.players.sample]))
        embed.add_field(name="Online / Max", value=f"{status.players.online} / {status.players.max}")

        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Minecraft(bot))
