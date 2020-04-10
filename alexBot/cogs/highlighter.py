import logging
import re

import discord
from discord.ext import commands

log = logging.getLogger(__name__)


class Highlighter(Cog):
    @commands.Cog.listener()
    async def on_message(self, message):
        if self.bot.location == 'dev' or message.guild is None:
            return
      if message.guild.id in self.bot.config.listenServers:
        if any(each in message.content for each in self.bot.config.listens):
          await _bot.owner.send(f"highlight: {messasge.author.mention} ({message.author}) in {message.channel.mention} ({message.channel})\n{message.jump_url}\n\n{message.content}")


def setup(bot):
    bot.add_cog(Highlighter(bot))
