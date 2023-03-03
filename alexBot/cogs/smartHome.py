import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Dict

import asyncio_mqtt as aiomqtt
import discord
from asyncio_mqtt.types import PayloadType
from discord.ext import tasks

from ..tools import Cog, get_json

if TYPE_CHECKING:
    from alexBot.cogs.mqttDispatcher import HomeAssistantIntigreation
    from bot import Bot


log = logging.getLogger(__name__)

TABLE = defaultdict(lambda: "💨")
TABLE['not_home'] = TABLE['not_home']  # add entry for .items of the default value
TABLE['home'] = "🏠"
TABLE['Walmart'] = "🏪"
TABLE["Garrett's Home"] = "🏠"
GUILD = 791528974442299412
MEMBERS = {'alex': 108429628560924672, 'garrett': 326410251546918913}
NEWLINE = '\n'
USER_TO_HA_DEVICE = {
    108429628560924672: 'mobile_app_pixel_7_pro',
    326410251546918913: 'mobile_app_game_s_iphone',
}


class PhoneMonitor(Cog):
    def __init__(self, bot: "Bot"):
        super().__init__(bot)
        self.mqttCog: "HomeAssistantIntigreation" = None

    @Cog.listener()
    async def on_ha_update_location(self, name: str, location: PayloadType):
        print('HERE!')
        log.info(f"HA update: {name} -> {location}")
        await self.bot.wait_until_ready()

        if name in MEMBERS:
            g = self.bot.get_guild(GUILD)
            member: discord.Member = g.get_member(MEMBERS[name])
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
        if name in MEMBERS:
            member = g.get_member(MEMBERS[name])
            if not member or not member.voice:
                return
            if command == 'mute':
                await member.edit(mute=not member.voice.mute)
            elif command == 'deafen':
                await member.edit(deafen=not member.voice.deaf, mute=not member.voice.deaf)
            elif command == 'disconnect':
                await member.move_to(None)

    @Cog.listener()
    async def on_voice_state_update(
        self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ):
        channel = before.channel or after.channel
        if self.mqttCog is None:
            self.mqttCog: "HomeAssistantIntigreation" = self.bot.get_cog("HomeAssistantIntigreation")
        if before.channel and after.channel and before.channel == after.channel:
            return  # noone moved
        on_mobile = [
            v for m, v in MEMBERS.items() if channel.guild.get_member(v) and channel.guild.get_member(v).is_on_mobile()
        ]
        log.debug(f"on_mobile: {on_mobile}")
        for user in on_mobile:
            log.debug(f"checking {user}")
            SELF_MOVED = user == member.id
            message = None
            if before.channel and after.channel and (before.channel != after.channel):
                if user in [user.id for user in before.channel.members]:
                    # person left chat to another channel in server
                    if SELF_MOVED:
                        message = f"you were moved to {after.channel.name}\n\nCurrent members are:\n{NEWLINE.join([m.name for m in after.channel.members])}"
                    else:
                        message = f"{member.name} was moved to {after.channel.name}\n\nCurrent members are:\n{NEWLINE.join([m.name for m in after.channel.members])}"
                if user in [user.id for user in after.channel.members]:
                    # person joined chat from another channel in server
                    message = f"{member.name} joined {after.channel.name}\n\nCurrent members are:\n{NEWLINE.join([m.name for m in after.channel.members])}"
            if before.channel and not after.channel and user in [user.id for user in before.channel.members]:
                # person left chat
                message = f"{member.name} left {before.channel.name}\n\nCurrent members are:\n{NEWLINE.join([m.name for m in before.channel.members])}"
                pass
            if not before.channel and after.channel and user in [user.id for user in after.channel.members]:
                # person joined chat
                message = f"{member.name} joined {after.channel.name}\n\nCurrent members are:\n{NEWLINE.join([m.name for m in after.channel.members])}"
            log.debug(f"message: {message}")
            if message:
                await self.mqttCog.mqttPublish(f"alex-bot/send_message/{USER_TO_HA_DEVICE[user]}", message)


async def setup(bot: "Bot"):
    await bot.add_cog(PhoneMonitor(bot))
