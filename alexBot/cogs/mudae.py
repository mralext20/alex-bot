import logging
from typing import TYPE_CHECKING

import discord
from datetime import datetime, timedelta

from ..tools import Cog

from typing import Optional

if TYPE_CHECKING:
    from bot import Bot


log = logging.getLogger(__name__)


class Mudae(Cog):
    def __init__(self, bot: "Bot"):
        super().__init__(bot)
        self.lastPinged: Optional[datetime] = None
        self.lastMessage: Optional[datetime] = None

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.channel.id != 1077272164887183450:
            return
        if message.content.lower() in ["$m", "$mg", "$ma"]:
            if self.lastMessage is None:
                self.lastMessage = datetime.now()
            elif datetime.now() - self.lastMessage < timedelta(seconds=60):
                self.lastMessage = datetime.now()
                return

            if self.lastPinged is None:
                self.lastPinged = datetime.now()
            elif datetime.now() - self.lastPinged < timedelta(minutes=5):
                return
            self.lastPinged = datetime.now()
            await message.channel.send("<@&1251159714532691979>", allowed_mentions=discord.AllowedMentions(roles=True))


async def setup(bot: "Bot"):
    await bot.add_cog(Mudae(bot))
