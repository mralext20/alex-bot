import logging
import re

import discord
import mcstatus
from discord import app_commands
from typing import Optional

from ..tools import Cog

log = logging.getLogger(__name__)

REMOVE_SECTION = re.compile("(\U000000a7.)")


class Minecraft(Cog):
    @app_commands.command()
    async def mc-status(self, interaction: discord.Interaction, server: Optional[str] = None):
        # a!mcStatus
        # -> guild.Minecraft
        if server is None and interaction.guild is not None:
            gd = await self.bot.db.get_guild_data(interaction.guild.id)
            server = gd.config.minecraft if gd.config.minecraft else None
            if server is None:
                return await interaction.response.send_message(
                    "please provide a server via argument or with `config set guild.Minecraft <SERVER>`",
                    ephemeral=True,
                )

        try:
            mcserver = mcstatus.MinecraftServer.lookup(server)
            status = await mcserver.async_status()
        except mcstatus:
            return await interaction.response.send_message("an error occured, the server may be down..")

        embed = discord.Embed(description=REMOVE_SECTION.sub('', status.description['text']))

        embed.title = f"{mcserver.host}:{mcserver.port}"

        if status.players.sample:
            embed.add_field(name="players", value='\n'.join([player.name for player in status.players.sample]))
        embed.add_field(name="Online / Max", value=f"{status.players.online} / {status.players.max}")

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Minecraft(bot))
