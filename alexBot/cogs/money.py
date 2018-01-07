# -*- coding: utf-8 -*-

from discord.ext import commands
import discord
from ..tools import Cog
import random
import logging
import asyncio

from ..tools import get_wallet
from ..tools import get_guild_config
from ..tools import update_wallet
from ..tools import TransactionError
from ..tools import BotError
from ..tools import CoinConverter

log = logging.getLogger(__name__)


class Money(Cog):
    """The description for Money goes here."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.lock = False
        self.money_cooldown = []

    @commands.command()
    @commands.is_owner()
    async def write(self, ctx, target: discord.Member, amount: CoinConverter):
        """sets the amount that a user has. owner only."""
        old = await get_wallet(self.bot, target.id)
        await update_wallet(self.bot, target.id, amount)
        await ctx.send(f"set {target}'s wallet to {amount}, was {old}")

    @commands.command()
    async def wallet(self, ctx, target: discord.Member=None):
        if target is None:
            target = ctx.author
        wallet = await get_wallet(self.bot, target.id)
        await ctx.send(f"wallet for {target} is {wallet:.2f}")

    @commands.command()
    async def transfer(self, ctx, target: discord.Member, amount: CoinConverter):
        """transfers an amount of money from your wallet to the target's wallet."""
        author_wallet = await get_wallet(self.bot, ctx.author.id)
        target_wallet = await get_wallet(self.bot, target.id)
        try:
            assert author_wallet > amount
        except AssertionError:
            raise TransactionError("you don't have enough funds for that")
        await update_wallet(self.bot, ctx.author.id, author_wallet-amount)
        await update_wallet(self.bot, target.id, target_wallet+amount)
        # TODO: atomic wallet transfers -> also line 67
        await ctx.send(f"sent {amount} to {target.display_name}")

    async def on_message(self, message: discord.Message):
        try:
            gcfg = await get_guild_config(self.bot, message.guild.id)
            assert gcfg['money'] is True
        except (AssertionError, AttributeError):
            # not in guild
            return
        if message.author.id in self.money_cooldown:
            # user recently got money
            return
        chance = random.random()  # get this message's percent chance
        if chance < self.bot.config.money['CHANCE']:
            try:
                old = await get_wallet(self.bot, message.author.id)
            except BotError:
                return
            log.info(f'gave {message.author} money')
            if not gcfg['hide_coins']:
                await message.add_reaction(self.bot.config.money['REACTION'])
            self.money_cooldown.append(message.author.id)
            await update_wallet(self.bot, message.author.id, old + self.bot.config.money['PER_MESSAGE'])
            await asyncio.sleep(5)
            if not gcfg['hide_coins']:
                await message.remove_reaction(self.bot.config.money['REACTION'], self.bot.user)
            await asyncio.sleep(300)
            self.money_cooldown.remove(message.author.id)
            return

    @commands.command()
    async def top(self, ctx):
        """returns a set of memebers and their wallets, based on who has the most"""
        ret = ""
        members = await self.bot.pool.fetch("""SELECT * FROM bank SORT ORDER BY amount DESC LIMIT 5""")
        # list constructor
        members = [(self.bot.get_user(r['owner']).mention, r['amount']) for r in members]
        c = 1
        for i in members:
            ret += f'{c}: {i[0]} has {i[1]}\n'
            c += 1
        emb = discord.Embed()
        emb.description = ret
        await ctx.send(embed=emb)


def setup(bot):
    bot.add_cog(Money(bot))
