# -*- coding: utf-8 -*-
from ..tools import Cog
from discord.ext import commands
import discord
from datetime import datetime


# bots which when going not offline -> offline we send the owner a dm
MONITORED_BOTS = {
    288369203046645761: 69198249432449024,  # Mousey, FrostLuma
}


class Memework(Cog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.archive_cat = self.bot.get_channel(355886867285147648)
        self.rowboat_log = self.bot.get_channel(303658324652589057)
        self.dog_log     = self.bot.get_channel(336159533124812800)

    @commands.command()
    @commands.bot_has_role("Rowboat")
    @commands.has_permissions(manage_channels=True)
    async def archive(self, ctx: commands.Context, channel: discord.TextChannel=None):
        if channel is None:
            channel = ctx.channel
        try:
            assert ctx.guild.id == 295341979800436736
        except AssertionError:
            await ctx.send("this only works in the memework guild."
                           "pls tell Alex from Alaska to unload this.")
        try:
            assert isinstance(channel, discord.TextChannel)
        except AssertionError:
            await ctx.send("you idiot i don't know what that is")
            return

        await channel.edit(category=self.archive_cat,
                           sync_permissions=True,
                           name=f"archived-{channel.name}",
                           reason=f"archived by {ctx.author.name}")
        await channel.send(f"this channel was archived by {ctx.author} at {datetime.utcnow().strftime('%H:%M')} UTC.")
        await ctx.send(f"archived {channel.mention}")

        await self.dog_log.send(f"`[{datetime.utcnow().strftime('%H:%m')}]`"
                                f"\U0001f6e0 {ctx.author} (`{ctx.author.id}`) Archived "
                                f"{channel} (`{channel.id}`)")

        await self.rowboat_log.send(f"`[{datetime.utcnow().strftime('%H:%m:%S')}]`"
                                    f"\U0001f6e0 {ctx.author} (`{ctx.author.id}`) Archived "
                                    f"**{channel}**")

    async def on_member_update(self, before: Member, after: Member):
        if before.id not in MONITORED_BOTS:
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
        owner = self.bot.get_user(MONITORED_BOTS[member.id])

        await owner.send(f'`[{now}]` \N{WARNING SIGN} `{before} {before.id}` just went offline')


def setup(bot):
    bot.add_cog(Memework(bot))
