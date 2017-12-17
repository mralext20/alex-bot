# -*- coding: utf-8 -*-

from discord.ext import commands
import discord
from ..tools import Cog
from random import choice
import logging
import asyncio

from ..tools import get_wallet
from ..tools import get_guild_config
from ..tools import update_wallet
from ..tools import TransactionError

log = logging.getLogger(__name__)


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
        await ctx.send(f"wallet for {target} is {wallet:.2f}")


    @commands.command()
    async def transfer(self, ctx, target:discord.Member, amount:float):
        """transfers an amount of money from your wallet to the target's wallet."""
        author_wallet = await get_wallet(self.bot, ctx.author.id)
        target_wallet = await get_wallet(self.bot, target.id)
        try:
            assert author_wallet > amount
        except AssertionError:
            raise TransactionError("you don't have enough funds for that")
        await update_wallet(self.bot, ctx.author.id, author_wallet-amount)
        await update_wallet(self.bot, target.id, target_wallet+amount)
        # TODO: make a modify_wallet func that takes a float and applies that value to the target_wallet when you do that also use it on line #67
        await ctx.send(f"sent {amount} to {target.display_name}")


    async def on_message(self, message:discord.Message):
        try:
            gcfg = await get_guild_config(self.bot, message.guild.id)
            assert gcfg['money'] == True
        except (AssertionError, AttributeError):
            # not in guild
            return
        chance = choice(range(0, 100)) / 100 # get this message's percent chance
        if chance < self.bot.config.money['CHANCE']:
            log.info(f'gave {message.author} money')
            await message.add_reaction(self.bot.config.money['REACTION'])
            old = await get_wallet(self.bot, message.author.id)
            await update_wallet(self.bot, message.author.id, old + self.bot.config.money['PER_MESSAGE'])
            await asyncio.sleep(5)
            await message.remove_reaction(self.bot.config.money['REACTION'], self.bot.user)
            return


def setup(bot):
    bot.add_cog(Money(bot))
