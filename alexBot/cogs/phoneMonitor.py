import asyncio
import logging
from typing import TYPE_CHECKING

from discord.ext import tasks

from ..tools import Cog

if TYPE_CHECKING:
    from bot import Bot


log = logging.getLogger(__name__)

TABLE = {
    0: "Alex's Phone is At Home",
    1: "Alex's Phone is Away From Home",
}


class PhoneMonitor(Cog):
    def __init__(self, bot: "Bot"):
        super().__init__(bot)
        self.phone_update.start()

    @tasks.loop(minutes=10)
    async def phone_update(self):
        ping = await asyncio.create_subprocess_shell("ping -c 1 192.168.1.150 -W 1")
        ret = await ping.wait()
        log.debug(f"detected phone, ret = {ret}, table is {TABLE[ret]}")
        alex = self.bot.get_guild(791528974442299412).me
        await alex.edit(nick=TABLE[ret])

    @phone_update.before_loop
    async def before_phone_updates(self):
        await self.bot.wait_until_ready()

    def cog_unload(self):
        self.phone_update.cancel()


async def setup(bot: "Bot"):
    if bot.location == "dev":
        return
    await bot.add_cog(PhoneMonitor(bot))
