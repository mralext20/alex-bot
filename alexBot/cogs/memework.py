# -*- coding: utf-8 -*-
from ..tools import Cog
import discord
from datetime import datetime


class Memework(Cog):
    @discord.ext.commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.id not in self.bot.config.monitored_bots:
            return

        if before.status is discord.Status.offline:
            return

        if after.status is not discord.Status.offline:
            return

        # see if this guild has the lowest ID of all mutual guilds we share with the bot
        # this is due to presence updates being dispatched once per guild, we don't want to dm more than once
        guilds = sorted(self.bot.guilds, key=lambda x: x.id)
        lowest_mutual = discord.utils.find(lambda x: x.get_member(before.id) is not None, guilds)

        if not lowest_mutual == before.guild:
            return

        now = datetime.utcnow().strftime('%H:%M')
        owner = self.bot.get_user(self.bot.config.monitored_bots[before.id])

        await owner.send(f'`[{now}]` \N{WARNING SIGN} `{before} {before.id}` just went offline')


def setup(bot):
    bot.add_cog(Memework(bot))
