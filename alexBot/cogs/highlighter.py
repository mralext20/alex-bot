import logging
import re

from ..tools import Cog

import discord
from discord.ext import commands

log = logging.getLogger(__name__)


class Highlighter(Cog):
    @commands.Cog.listener()
    async def on_message(self, message):
        if self.bot.location == 'dev' or message.guild is None:
            return
        if message.guild.id in self.bot.config.listenServers and message.author.id != self.bot.owner.id:
            if any(each in message.content for each in self.bot.config.listens):
                await self.bot.owner.send(
                    f"highlight: {message.author.mention}({message.author})"
                    f"in {message.channel.mention}({message.channel})"
                    f"\n{message.jump_url}\n\n{message.content}")


def setup(bot):
    bot.add_cog(Highlighter(bot))
