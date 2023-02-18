# -*- coding: utf-8 -*-

import asyncio
import datetime
from asyncio import Task
from typing import Dict

import discord
from discord.member import VoiceState

from ..tools import Cog

NERDIOWO_GUILD_ID = 791528974442299412
ADMIN_CATEGORY_ID = 822958326249816095
LOGGING_CHANNEL = 791530687102451712


class VoiceLog(Cog):
    def __init__(self, bot: "Bot"):
        super().__init__(bot)
        self.waiting_for_afk: Dict[int, Task] = {}

    @Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: VoiceState, after: VoiceState):
        """
        only for actions in nerdiowo
        hide events that do with ther admin category in any way
        """
        if member.id in self.waiting_for_afk:
            self.waiting_for_afk[member.id].cancel()
            del self.waiting_for_afk[member.id]

        if member.guild.id != NERDIOWO_GUILD_ID:
            return
        if before.channel and before.channel.category_id == ADMIN_CATEGORY_ID:
            before.channel = None
        if after.channel and after.channel.category_id == ADMIN_CATEGORY_ID:
            after.channel = None
        if after.channel == member.guild.afk_channel:
            self.waiting_for_afk[member.id] = self.bot.loop.create_task(self.afk(member))
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

    async def afk(self, member: discord.Member):
        await asyncio.sleep(60 * 60)  # 1 hour

        # we didn't get cancled, let's send a button
        class AFKView(discord.ui.View):
            def __init__(self, member: discord.Member, task: Task):
                super().__init__()
                self.task = task
                self.member = member

            @discord.ui.button(label="I'm still here", style=discord.ButtonStyle.green)
            async def still_here(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.send_message("Thanks for letting us know!", ephemeral=True)
                self.task.cancel()
                self.stop()

        await member.send(
            "You have been afk for 1 hour, are you still there?", view=AFKView(member, self.waiting_for_afk[member.id])
        )
        await asyncio.sleep(60 * 5)  # wait 5 minutes
        # we didn't get cancled, let's kick the user
        await member.move_to(None, reason="AFK for 1 hour")

    async def Cog_unload(self):
        for task in self.waiting_for_afk.values():
            task.cancel()


async def setup(bot):
    await bot.add_cog(VoiceLog(bot))
