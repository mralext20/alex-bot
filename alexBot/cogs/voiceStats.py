import datetime
import logging

import discord
from discord.ext import commands

from alexBot.classes import GuildData, VoiceStat
from alexBot.tools import Cog

log = logging.getLogger(__name__)


class VoiceStats(Cog):
    @Cog.listener()
    async def on_voice_state_update(
        self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ):
        if before.channel is not None and after.channel is not None:  # check that joined or left a voice call
            return
        channel = before.channel or after.channel
        # ?? can we gather data from this guild?
        gd = await self.bot.db.get_guild_data(channel.guild.id)
        if not gd.config.collectVoiceData:
            return

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
        if not LEAVING and len([m for m in after.channel.members if not m.bot]) == 1:
            FIRST = True
        else:
            FIRST = False
        if LEAVING and LAST:
            # definitly ending of a call
            await self.ending_a_call(channel, gd)

        if not LEAVING and FIRST:
            await self.starting_a_call(channel, gd)

        log.debug(f"{LAST=}, {LEAVING=}, {FIRST=}")

    async def starting_a_call(self, channel: discord.VoiceChannel, guildData: GuildData):
        log.debug(f"starting a call: {channel=}")
        if guildData.voiceStat.currently_running:
            log.debug("second call started in guild")
            return
        guildData.voiceStat.last_started = datetime.datetime.now()
        guildData.voiceStat.currently_running = True

        await self.bot.db.save_guild_data(channel.guild.id, guildData)

    async def ending_a_call(self, channel: discord.VoiceChannel, gd: GuildData):
        log.debug(f"ending a call: {channel=}")
        guild = channel.guild
        if self.any_other_voice_chats(guild):
            log.debug("late return: other VC in guild")
            return  # the call continues in another channel
        if not gd.voiceStat.currently_running:
            # odd state, ignore
            return
        current_session_length = datetime.datetime.now() - gd.voiceStat.last_started
        if gd.voiceStat.longest_session < current_session_length:
            gd.voiceStat.longest_session = current_session_length

        gd.voiceStat.average_duration_raw = (
            (gd.voiceStat.total_sessions * gd.voiceStat.average_duration_raw) + current_session_length.total_seconds()
        ) / (gd.voiceStat.total_sessions + 1)
        gd.voiceStat.total_sessions += 1
        gd.voiceStat.currently_running = False
        await self.bot.db.save_guild_data(channel.guild.id, gd)

    @commands.command()
    async def voiceStats(self, ctx: commands.Context):
        vd = (await self.bot.db.get_guild_data(ctx.guild.id)).voiceStat
        embed = discord.Embed()
        if self.any_other_voice_chats(ctx.guild):
            embed.add_field(name="Current Session Length", value=datetime.datetime.now() - vd.last_started)
        embed.add_field(name="longest session", value=vd.longest_session)
        embed.add_field(name="Average Session Length", value=vd.average_duration)
        embed.add_field(name="Total Sessions", value=vd.total_sessions)
        await ctx.send(embed=embed)

    @staticmethod
    def any_other_voice_chats(guild: discord.Guild) -> bool:
        return any([len([m for m in vc.members if not m.bot]) > 0 for vc in guild.voice_channels])


def setup(bot):
    bot.add_cog(VoiceStats(bot))
