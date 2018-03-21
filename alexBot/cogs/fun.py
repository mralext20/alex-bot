import logging
import re

from ..tools import Cog
from ..tools import get_guild_config

log = logging.getLogger(__name__)
ayygen = re.compile('[aA][yY][Yy][yY]*')


class Fun(Cog):
    """contains the on message for ayy"""
    async def on_message(self, message):
        if self.bot.location == 'laptop' or message.guild is None:
            return
        if (await get_guild_config(self.bot, message.guild.id))['ayy'] is False:
            return

        if ayygen.fullmatch(message.content):
            await message.channel.send("lmao")


def setup(bot):
    bot.add_cog(Fun(bot))
