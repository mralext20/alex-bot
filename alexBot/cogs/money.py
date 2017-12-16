# -*- coding: utf-8 -*-

from discord.ext import commands
import discord
from ..tools import Cog

from ..tools import get_wallet
from ..tools import get_guild_config
from ..tools import update_wallet

class Money(Cog):
    """The description for Money goes here."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.lock = False


    @commands.command()
    @commands.is_owner()
    async def write(self, ctx, target: discord.Member, amount):
        """sets the amount that a user has. owner only."""
        old = await get_wallet(self.bot, target.id)
        await update_wallet(self.bot, target.id, amount)
        await ctx.send(f"set {target}'s wallet to {amount}, was {old}")

    @commands.command()
    async def wallet(self, ctx:commands.Context, target:discord.Member=None):
        if target is None:
            target = ctx.author
        wallet = await get_wallet(self.bot,target.id)
        await ctx.send(f"wallet for {target} is {wallet}")


def setup(bot):
    bot.add_cog(Money(bot))
