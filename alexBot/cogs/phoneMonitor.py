import logging
from typing import TYPE_CHECKING

from discord.ext import tasks
from collections import defaultdict
from ..tools import Cog, get_json

if TYPE_CHECKING:
    from bot import Bot


log = logging.getLogger(__name__)

TABLE = defaultdict(lambda: "Alex is Away")
TABLE['home'] = "Alex is At Home"
TABLE['walmart'] = "Alex is At Work"


class PhoneMonitor(Cog):
    def __init__(self, bot: "Bot"):
        super().__init__(bot)
        self.phone_update.start()

    @tasks.loop(minutes=1)
    async def phone_update(self):
        ret = await get_json(
            self.bot.session,
            f"{self.bot.config.hass_host}/api/states/{self.bot.config.hass_target}",
            headers={'Authorization': self.bot.config.hass_token},
        )
        ret = ret['state']
        log.debug(f"asked HA, ret = {ret}, table is {TABLE[ret]}")
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
