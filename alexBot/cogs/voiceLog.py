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
    async def on_voice_state_update(self, member: discord.Member, before: VoiceState, after: VoiceState):
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
            await channel.send(f"{stamp} 🎤 {member.mention} joined {after.channel.name}")
        elif before.channel is not None and after.channel is None:
            # left
            await channel.send(f"{stamp} ☎️ {member.mention} left {before.channel.name}")
        elif before.channel != after.channel:
            # moved
            await channel.send(f"{stamp} 🎚️ {member.mention}  moved from {before.channel.name} to {after.channel.name}")

        if after.channel and after.channel.user_limit == 1 and len(after.channel.members) == 1:
            # give the user channel override for manage menbers
            await after.channel.set_permissions(member, overwrite=discord.PermissionOverwrite(move_members=True))
        if before.channel and before.channel.user_limit == 1:
            # remove the user channel override for manage menbers
            await before.channel.set_permissions(member, overwrite=None)


async def setup(bot):
    await bot.add_cog(VoiceLog(bot))
