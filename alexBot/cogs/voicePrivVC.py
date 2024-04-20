# -*- coding: utf-8 -*-

import asyncio
import datetime
from asyncio import Task
from typing import Dict, List, TYPE_CHECKING


from alexBot import database as db


if TYPE_CHECKING:
    from bot import Bot

import discord
from discord.member import VoiceState

from ..tools import Cog


class VoicePrivVC(Cog):
    def __init__(self, bot: "Bot"):
        super().__init__(bot)
        self.waiting_for_afk: Dict[int, Task] = {}
        self.beingShaken: Dict[int, bool] = {}

    @Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: VoiceState, after: VoiceState):
        """
        only for actions in nerdiowo
        hide events that do with ther admin category in any way
        """
        async with db.async_session() as session:
            gd = await session.get(db.GuildConfig, member.guild.id)
            if not gd:
                gd = db.GuildConfig(guildId=member.guild.id)
                session.add(gd)
                await session.commit()
        if gd.privateOnePersonVCs:
            if after.channel and after.channel.user_limit == 1 and len(after.channel.members) == 1:
                # give the user channel override for manage menbers
                await after.channel.set_permissions(member, overwrite=discord.PermissionOverwrite(move_members=True))
            if before.channel and before.channel.user_limit == 1:
                # remove the user channel override for manage menbers
                await before.channel.set_permissions(member, overwrite=None)


async def setup(bot):
    await bot.add_cog(VoicePrivVC(bot))
