# -*- coding: utf-8 -*-

import datetime

import discord
from discord.member import VoiceState

from ..tools import Cog

NERDIOWO_GUILD_ID = 791528974442299412
ADMIN_CATEGORY_ID = 822958326249816095
LOGGING_CHANNEL = 791530687102451712


class VoiceLog(Cog):
    @Cog.listener()
    async def on_voice_state_update(self, member: VoiceState, before: VoiceState, after: VoiceState):
        """
        only for actions in nerdiowo
        hide events that do with ther admin category in any way
        """
        if member.guild.id != NERDIOWO_GUILD_ID:
            return
        if before.channel and before.channel.category_id == ADMIN_CATEGORY_ID:
            before.channel = None
        if after.channel and after.channel.category_id == ADMIN_CATEGORY_ID:
            after.channel = None

        channel = self.bot.get_channel(LOGGING_CHANNEL)
        if not channel:
            return
        stamp = discord.utils.format_dt(datetime.datetime.now(), style="T")
        if before.channel is None and after.channel is not None:
            # joined
            await channel.send(f"{stamp} 🎤 {member.mention} (`{member.id}`) joined {after.channel.mention}")
        elif before.channel is not None and after.channel is None:
            # left
            await channel.send(f"{stamp} ☎️ {member.mention} (`{member.id}`) left {before.channel.mention}")
        elif before.channel != after.channel:
            # moved
            await channel.send(
                f"{stamp} 🎚️ {member.mention} (`{member.id}`) moved from {before.channel.mention} to {after.channel.mention}"
            )


async def setup(bot):
    await bot.add_cog(VoiceLog(bot))
