import asyncio
import datetime
import logging
import time
from typing import Optional, Union

import discord
from discord import app_commands
from sqlalchemy.ext.asyncio import AsyncSession

from alexBot.database import GuildConfig, UserConfig, VoiceStat, async_session, select
from alexBot.tools import Cog

log = logging.getLogger(__name__)


class VoiceStats(Cog):
    async def cog_load(self):
        self.bot.voiceCommandsGroup.add_command(
            app_commands.Command(
                name="stats",
                description="Tells you how long your average, longest, and current voice sessions is.",
                callback=self.voiceStats,
            )
        )

    async def cog_unload(self):
        self.bot.voiceCommandsGroup.remove_command("stats")

    @Cog.listener()
    async def on_voice_state_update(
        self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ):
        if before.channel is not None and after.channel is not None:  # check that joined or left a voice call
            return
        channel: Union[discord.VoiceChannel, discord.StageChannel] = before.channel or after.channel  # type: ignore
        # ?? can we gather data from this guild?
        gc = None
        async with async_session() as session:
            gc = await session.scalar(select(GuildConfig).where(GuildConfig.guildId == channel.guild.id))
            if not gc:
                gc = GuildConfig(guildId=channel.guild.id)
                session.add(gc)
                await session.commit()

            # ?? are we getting an event for someone leaving?
            if before.channel:
                LEAVING = True
            else:
                LEAVING = False
            # ?? were they the last person?
            if len([m for m in channel.members if not m.bot]) == 0:
                LAST = True
            else:
                LAST = False
            if not LEAVING and len([m for m in after.channel.members if not m.bot]) == 1:  # type: ignore  # after.channel is gareted if not leaving
                FIRST = True
            else:
                FIRST = False
            if LEAVING and LAST and gc.collectVoiceData:
                # definitly ending of a call
                await self.ending_a_call(channel, session)

            if not LEAVING and FIRST and gc.collectVoiceData:
                await self.starting_a_call(channel, session)

            uc = await session.scalar(select(UserConfig).where(UserConfig.userId == member.id))
            if not uc:
                uc = UserConfig(userId=member.id)
                session.add(uc)
                await session.commit()
            if uc.collectVoiceData:
                if LEAVING:
                    await self.member_leaving_call(member, channel, session)
                else:
                    await self.member_joining_call(member, channel, session)

            log.debug(f"{LAST=}, {LEAVING=}, {FIRST=}")

    async def starting_a_call(
        self,
        channel: Union[discord.VoiceChannel, discord.StageChannel],
        session: AsyncSession,
    ):
        vs = await session.scalar(select(VoiceStat).where(VoiceStat.id == channel.guild.id))
        if not vs:
            vs = VoiceStat(id=channel.guild.id)
            session.add(vs)
            await session.commit()
        log.debug(f"starting a call: {channel=}")
        if vs.recently_ended:
            log.debug("late return: recently_ended is true")
            return  # they reconnected
        vs.recently_ended = False
        if vs.currently_running:
            log.debug("second call started in guild")
            return
        vs.last_started = datetime.datetime.now()
        vs.currently_running = True

        session.add(vs)
        await session.commit()

    async def member_joining_call(
        self,
        member: discord.Member,
        channel: Union[discord.VoiceChannel, discord.StageChannel],
        session: AsyncSession,
    ):
        log.debug(f"{member=} joined {channel=}")
        vs = await session.scalar(select(VoiceStat).where(VoiceStat.id == member.id))
        if not vs:
            vs = VoiceStat(id=member.id)
            session.add(vs)
            await session.commit()
        if vs.recently_ended:
            log.debug("late return: recently_ended is true")
            return  # they reconnected

        vs.recently_ended = False

        vs.last_started = datetime.datetime.now()
        vs.currently_running = True

        session.add(vs)
        await session.commit()

    async def member_leaving_call(
        self,
        member: discord.Member,
        channel: Union[discord.VoiceChannel, discord.StageChannel],
        session: AsyncSession,
    ):
        log.debug(f"{member=} left {channel=}")
        vs = await session.scalar(select(VoiceStat).where(VoiceStat.id == member.id))
        if not vs:
            log.warn(f"{member=} left {channel=} but no voiceStat found")
            vs = VoiceStat(id=member.id)
            session.add(vs)
            await session.commit()
        if not vs.currently_running:
            # odd state, ignore
            return
        vs.recently_ended = True
        session.add(vs)
        await session.commit()

        await asyncio.sleep(30)  # wait 30 seconds for momnetary reconnects
        vs = await session.scalar(select(VoiceStat).where(VoiceStat.id == member.id))  # refresh data
        if not vs:
            log.warn(f"{member=} left late, {channel=} but no voiceStat found")
            return
        if not vs.recently_ended:
            log.debug("late return: recently_ended is false")

            return  # they reconnected
        vs.recently_ended = False

        current_session_length = datetime.datetime.now() - vs.last_started
        if vs.longest_session < current_session_length:
            vs.longest_session = current_session_length

        vs.average_duration = datetime.timedelta(
            seconds=(vs.total_sessions * vs.average_duration.total_seconds()) + current_session_length.total_seconds()
        ) / (vs.total_sessions + 1)
        vs.total_sessions += 1
        # check if user is active in another server we know about
        for guild in member.mutual_guilds:
            if guild.get_member(member.id).voice is not None:  # type:ignore
                log.debug(f"{member=} is active in {guild=}")
                break
        else:
            vs.currently_running = False
        session.add(vs)
        await session.commit()
        return

    async def ending_a_call(self, channel: Union[discord.VoiceChannel, discord.StageChannel], session: AsyncSession):
        log.debug(f"ending a call: {channel=}")
        guild = channel.guild
        if self.any_other_voice_chats(guild):
            log.debug("late return: other VC in guild")
            return  # the call continues in another channel
        vs = await session.scalar(select(VoiceStat).where(VoiceStat.id == guild.id))
        if not vs:
            log.warn(f"{guild=} left {channel=} but no voiceStat found")
            return
        if not vs.currently_running:
            # odd state, ignore
            return
        vs.recently_ended = True
        session.add(vs)
        await session.commit()

        await asyncio.sleep(30)  # wait 30 seconds for momnetary reconnects
        vs = await session.scalar(select(VoiceStat).where(VoiceStat.id == guild.id))  # refresh data
        if not vs:
            log.warn(f"{guild=} left late, data somhow deleted??? {channel=} but no voiceStat found")
            return
        if not vs.recently_ended:
            log.debug("late return: recently_ended is false")
            return
        vs.recently_ended = False
        current_session_length = datetime.datetime.now() - vs.last_started
        if vs.longest_session < current_session_length:
            vs.longest_session = current_session_length

        vs.average_duration = datetime.timedelta(
            (vs.total_sessions * vs.average_duration.total_seconds()) + current_session_length.total_seconds()
        ) / (vs.total_sessions + 1)
        vs.total_sessions += 1
        vs.currently_running = False
        session.add(vs)
        await session.commit()

    async def voiceStats(self, interaction: discord.Interaction, target: Optional[discord.User]):
        """tells you how long your average, longest, and current voice sessions is."""
        targets = [interaction.user, interaction.guild] if target is None else [target]
        embeds = []
        async with async_session() as session:
            for target in targets:
                embed = discord.Embed()
                vs = await session.scalar(select(VoiceStat).where(VoiceStat.id == target.id))
                if not vs:
                    vs = VoiceStat(id=target.id)
                    session.add(vs)
                    await session.commit()
                if isinstance(target, discord.Member):
                    embed.title = f"{target.display_name}'s Voice Stats"
                    embed.set_author(
                        name=target.display_name,
                        icon_url=target.avatar.url if target.avatar else target.default_avatar.url,
                    )
                elif isinstance(target, discord.Guild):
                    embed.title = f"{target.name}'s Voice Stats"
                    embed.set_author(name=target.name, icon_url=target.icon.url if target.icon else None)
                if vs.currently_running:
                    embed.add_field(
                        name="Current Session Length",
                        value=datetime.timedelta(
                            seconds=int((datetime.datetime.now() - vs.last_started).total_seconds())
                        ),
                    )
                embed.add_field(name="longest session", value=vs.longest_session)
                embed.add_field(name="Average Session Length", value=vs.average_duration)
                embed.add_field(name="Total Sessions", value=vs.total_sessions)
                embeds.append(embed)
            await interaction.response.send_message(embeds=embeds)

    @staticmethod
    def any_other_voice_chats(guild: discord.Guild) -> bool:
        return any([len([m for m in vc.members if not m.bot]) > 0 for vc in guild.voice_channels])


async def setup(bot):
    await bot.add_cog(VoiceStats(bot))
