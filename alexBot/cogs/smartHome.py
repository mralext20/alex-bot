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
TABLE['not_home'] = TABLE['not_home']  # add entry for .items of the default value
TABLE['home'] = "🏠"
TABLE['Walmart'] = "🏪"
TABLE['Garretts Home'] = "🏠"
GUILD = 791528974442299412
members = {'alex': 108429628560924672, 'garrett': 326410251546918913}


class PhoneMonitor(Cog):
    @Cog.listener()
    async def on_ha_update_location(self, name: str, location: PayloadType):
        print('HERE!')
        log.info(f"HA update: {name} -> {location}")
        await self.bot.wait_until_ready()

        if name in members:
            g = self.bot.get_guild(GUILD)
            member: discord.Member = g.get_member(members[name])
            name = member.display_name
            for _, locator in TABLE.items():
                name = name.rstrip(locator)

            name += TABLE[location]
            log.info(f"Changing {member.display_name} to {name}")
            await member.edit(nick=name)

    @Cog.listener()
    async def on_ha_vc_control(self, name: str, command: PayloadType):
        log.info(f"HA vc control: {name} -> {command}")
        await self.bot.wait_until_ready()
        g = self.bot.get_guild(GUILD)
        assert g is not None
        if name in members:
            member = g.get_member(members[name])
            if not member or not member.voice:
                return
            if command == 'mute':
                await member.edit(mute=not member.voice.mute)
            elif command == 'deafen':
                await member.edit(deafen=not member.voice.deaf, mute=not member.voice.deaf)
            elif command == 'disconnect':
                await member.move_to(None)


async def setup(bot: "Bot"):
    await bot.add_cog(PhoneMonitor(bot))
