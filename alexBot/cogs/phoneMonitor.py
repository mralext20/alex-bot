import logging
from collections import defaultdict
from typing import TYPE_CHECKING

import asyncio_mqtt as aiomqtt
import discord
from asyncio_mqtt.types import PayloadType
from discord.ext import tasks

from ..tools import Cog, get_json

if TYPE_CHECKING:
    from bot import Bot


log = logging.getLogger(__name__)

TABLE = defaultdict(lambda: "💨")
TABLE['home'] = "🏠"
TABLE['Walmart'] = "🏪"
TABLE['garrett'] = "🏠"

GUILD = 791528974442299412
members = {'alex': 108429628560924672, 'garrett': 326410251546918913}


class PhoneMonitor(Cog):
    @Cog.listener()
    async def on_ha_update_location(self, ha_name: aiomqtt.Topic, location: PayloadType):
        await self.bot.wait_until_ready()
        good_name = ha_name.value.lstrip("alex-bot/")
        if ha_name in members:
            g = self.bot.get_guild(GUILD)
            member: discord.Member = await g.get_member(members[good_name])
            name = member.display_name
            for _, locator in TABLE.items():
                name = name.rstrip(locator)

            name += TABLE[location]
            await member.edit(nick=name)


async def setup(bot: "Bot"):
    if bot.location == "dev":
        return
    await bot.add_cog(PhoneMonitor(bot))
