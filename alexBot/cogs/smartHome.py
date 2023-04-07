import logging
import typing
from collections import defaultdict
from typing import TYPE_CHECKING, Dict, List

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
TABLE['Boston'] = "🎮"
GUILD = 791528974442299412
MEMBERS = {  # ha-name: (discord-id, [guild-ids])
    'alex': (108429628560924672, [791528974442299412, 384843279042084865]),
    'garrett': (326410251546918913, [791528974442299412, 384843279042084865]),
}
NEWLINE = '\n'
USER_TO_HA_DEVICE = {
    108429628560924672: 'mobile_app_pixel_7_pro',
    326410251546918913: 'mobile_app_game_s_iphone',
}


class PhoneMonitor(Cog):
    def __init__(self, bot: "Bot"):
        super().__init__(bot)
        self.mqttCog: "HomeAssistantIntigreation" = None
        self.notifiable: List[int] = list(USER_TO_HA_DEVICE.keys())

    @discord.app_commands.command(name="ha-vc-notifs", description="Toggle voice channel notifications for your phone")
    @discord.app_commands.guilds(GUILD)
    async def ha_vc_notifs(self, interaction: discord.Interaction):
        if interaction.user.id not in USER_TO_HA_DEVICE:
            await interaction.response.send_message("You can not use this command", ephemeral=True)
            return
        if interaction.user.id in self.notifiable:
            self.notifiable.remove(interaction.user.id)
            await interaction.response.send_message(
                "You will no longer be notified of voice channel changes", ephemeral=True
            )
            log.debug(f"Removing {interaction.user.id} from notifiable")
        else:
            self.notifiable.append(interaction.user.id)
            log.debug(f"Adding {interaction.user.id} to notifiable")
            await interaction.response.send_message("You will now be notified of voice channel changes", ephemeral=True)

    @Cog.listener()
    async def on_ha_update_location(self, name: str, location: PayloadType):
        log.info(f"HA update: {name} -> {location}")
        await self.bot.wait_until_ready()

        if name in MEMBERS:
            for g in MEMBERS[name][1]:
                g = self.bot.get_guild(GUILD)

                member: discord.Member = g.get_member(MEMBERS[name])
                if not member:
                    continue
                name = member.display_name
                for _, locator in TABLE.items():
                    name = name.rstrip(locator)

                name += TABLE[location]
                log.info(f"Changing {member.display_name} to {name}")
                try:
                    await member.edit(nick=name)
                except discord.errors.Forbidden:
                    pass  # permission fault, probably because server owner
            if member.id not in self.notifiable and location == "Walmart":
                self.notifiable.append(member.id)
                log.info(f"Adding {member.display_name} to notifiable for being at walmart")

    @Cog.listener()
    async def on_ha_vc_control(self, name: str, command: PayloadType):
        log.info(f"HA vc control: {name} -> {command}")
        await self.bot.wait_until_ready()
        if name in MEMBERS:
            user = self.bot.get_user(MEMBERS[name][0])
            if not user:
                return
            targets = [g for g in user.mutual_guilds if g.get_member(user.id).voice]
            if not targets:
                return
            member = targets[0].get_member(user.id)
            if command == 'mute':
                await member.edit(mute=not member.voice.mute)
            elif command == 'deafen':
                await member.edit(deafen=not member.voice.deaf, mute=not member.voice.deaf)
            elif command == 'disconnect':
                await member.edit(deafen=False, mute=False)
                await member.move_to(None)

    @Cog.listener()
    async def on_voice_state_update(
        self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ):
        channel: discord.VoiceChannel = before.channel or after.channel
        if self.mqttCog is None:
            self.mqttCog: "HomeAssistantIntigreation" = self.bot.get_cog("HomeAssistantIntigreation")
        if before.channel and after.channel and before.channel == after.channel:
            return  # noone moved

        for user in self.notifiable:
            oldAfter = after.channel
            log.debug(f"checking {user}")
            SELF_MOVED = user == member.id
            message = None
            tc: List[discord.Member] = []
            if not (targtetMember := channel.guild.get_member(user)):
                return  #  user not in server
            if after.channel and not after.channel.permissions_for(targtetMember).view_channel:
                after.channel = None

            if before.channel and after.channel and (before.channel != after.channel):
                if user in [user.id for user in before.channel.members]:
                    # person left chat to another channel in server
                    log.debug(f"{member.name} moved from {before.channel.name} to {after.channel.name}")
                    message = f"{member.name} was moved to {after.channel.name}"
                    tc = after.channel.members
                if user in [user.id for user in after.channel.members]:
                    # person joined chat from another channel in server
                    if SELF_MOVED:
                        log.debug(f"Self moved from {before.channel.name} to {after.channel.name}")
                        message = f"you were moved to {after.channel.name}"
                    else:
                        log.debug(f"{member.name} moved from {before.channel.name} to {after.channel.name}")
                        message = f"{member.name} joined {after.channel.name}"

                    tc = after.channel.members

            if before.channel and not after.channel and user in [user.id for user in before.channel.members]:
                # person left chat
                log.debug(f"{member.name} left {before.channel.name}")
                message = f"{member.name} left {before.channel.name}"
                tc = before.channel.members
                pass
            if not before.channel and after.channel and user in [user.id for user in after.channel.members]:
                # person joined chat
                log.debug(f"{member.name} joined {after.channel.name}")
                message = f"{member.name} joined {after.channel.name}"
                tc = after.channel.members

            if message:
                message = message + f"\n\nCurrent members are:\n{NEWLINE.join([m.name for m in tc])}"
                log.debug(f"message: {message}")
                await self.mqttCog.mqttPublish(f"alex-bot/send_message/{USER_TO_HA_DEVICE[user]}", message)

            after.channel = oldAfter


async def setup(bot: "Bot"):
    await bot.add_cog(PhoneMonitor(bot))
