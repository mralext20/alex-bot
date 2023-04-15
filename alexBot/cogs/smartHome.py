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
            for gid in MEMBERS[name][1]:
                log.debug(f"Checking {name} in {gid}")
                g = self.bot.get_guild(gid)
                if not g:
                    log.debug(f"Skipping {name} because {gid} is not a valid guild")
                    continue
                member = g.get_member(MEMBERS[name][0])
                if not member:
                    log.debug(f"Skipping {name} because {MEMBERS[name][0]} is not a valid member in {g}")
                    continue
                g_name = member.display_name
                for _, locator in TABLE.items():
                    g_name = g_name.rstrip(locator)

                g_name += TABLE[location]
                log.info(f"Changing {member.display_name} in {g} to {g_name}")
                try:
                    await member.edit(nick=g_name)
                except discord.errors.Forbidden as e:
                    log.debug(e)
                    continue  # permission fault, probably because server owner
            if MEMBERS[name][0] not in self.notifiable and location == "Walmart":
                self.notifiable.append(MEMBERS[name][0])
                log.info(f"Adding {member.display_name} to notifiable for being at walmart")

    @Cog.listener()
    async def on_ha_vc_control(self, name: str, command: PayloadType):
        log.info(f"HA vc control: {name} -> {command}")
        await self.bot.wait_until_ready()
        mqttCog: HomeAssistantIntigreation = self.bot.get_cog("HomeAssistantIntigreation")
        if name in MEMBERS:
            user = self.bot.get_user(MEMBERS[name][0])
            if not user:
                return
            targets = [g for g in user.mutual_guilds if g.get_member(user.id).voice]
            if not targets:
                await mqttCog.mqttPublish(
                    f"alex-bot/send_message/{USER_TO_HA_DEVICE[user.id]}", "Err: i can't see what VC you are in"
                )
                return
            member = targets[0].get_member(user.id)
            try:
                if command == 'mute':
                    await member.edit(mute=not member.voice.mute)
                elif command == 'deafen':
                    await member.edit(deafen=not member.voice.deaf, mute=not member.voice.deaf)
                elif command == 'disconnect':
                    await member.edit(deafen=False, mute=False)
                    await member.move_to(None)
            except discord.errors.Forbidden as e:
                await mqttCog.mqttPublish(
                    f"alex-bot/send_message/{USER_TO_HA_DEVICE[user.id]}",
                    "Err: i don't have permission to do that in {member.guild}",
                )
            voiceState = targets[0].get_member(user.id).voice
            await self.send_notification(
                MEMBERS[name][0], f"ACK: {command}ed in {targets[0].name}", voiceState.channel.members
            )

    @staticmethod
    def render_voiceState(member: discord.Member) -> str:
        s = ""
        if member.voice.mute or member.voice.self_mute:
            s += "🙊"
        if member.voice.deaf or member.voice.self_deaf:
            s += "🙉"
        if member.voice.self_video:
            s += "📹"
        if member.voice.self_stream:
            s += "🔴"
        return s

    @Cog.listener()
    async def on_voice_state_update(
        self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ):
        channel: discord.VoiceChannel = before.channel or after.channel
        if before.channel and after.channel and before.channel == after.channel:
            return  # noone moved
        voiceLog = self.bot.get_cog('VoiceLog')
        if voiceLog:
            if voiceLog.beingShaken.get(member.id):
                return  # ignore person being shaken

        for user in self.notifiable:
            oldAfter = after.channel
            log.debug(f"checking {user}")
            SELF_MOVED = user == member.id
            message = None
            memberList: List[discord.Member] = []
            if not (targtetMember := channel.guild.get_member(user)):
                return  #  user not in server
            if after.channel and not after.channel.permissions_for(targtetMember).view_channel:
                after.channel = None

            if before.channel and after.channel and (before.channel != after.channel):
                if user in [user.id for user in before.channel.members]:
                    # person left chat to another channel in server
                    log.debug(f"{member.name} moved from {before.channel.name} to {after.channel.name}")
                    message = f"{member.name} was moved to {after.channel.name}"
                    memberList = before.channel.members
                if user in [user.id for user in after.channel.members]:
                    # person joined chat from another channel in server
                    if SELF_MOVED:
                        log.debug(f"Self moved from {before.channel.name} to {after.channel.name}")
                        message = f"you were moved to {after.channel.name}"
                    else:
                        log.debug(f"{member.name} moved from {before.channel.name} to {after.channel.name}")
                        message = f"{member.name} joined {after.channel.name}"

                    memberList = after.channel.members

            if before.channel and not after.channel and user in [user.id for user in before.channel.members]:
                # person left chat
                log.debug(f"{member.name} left {before.channel.name}")
                message = f"{member.name} left {before.channel.name}"
                memberList = before.channel.members
                pass
            if not before.channel and after.channel and user in [user.id for user in after.channel.members]:
                # person joined chat
                log.debug(f"{member.name} joined {after.channel.name}")
                message = f"{member.name} joined {after.channel.name}"
                memberList = after.channel.members

            if message:
                await self.send_notification(user, message, memberList)

            after.channel = oldAfter

    async def send_notification(self, user: int, message: str, members: List[discord.Member]):
        log.debug(f"message pre members: {message}")
        message = (
            message
            + f"\n\nCurrent members in your channel are:\n{NEWLINE.join([f'{m.name} {self.render_voiceState(m)}' for m in members])}"
        )
        log.debug(f"message post members : {message}")
        mqttCog: HomeAssistantIntigreation = self.bot.get_cog("HomeAssistantIntigreation")
        await mqttCog.mqttPublish(f"alex-bot/send_message/{USER_TO_HA_DEVICE[user]}", message)


async def setup(bot: "Bot"):
    await bot.add_cog(PhoneMonitor(bot))
