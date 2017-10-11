import asyncio
from discord.ext import commands
import discord
from motor import motor_asyncio as motor
import random

from ..tools import Cog
from ..tools import get_config_value


async def get_user(collection : motor.AsyncIOMotorCollection, ID: int):
    user = await collection.find_one({"ID": ID})
    if user is not None:
        return user
    else:
        await collection.insert_one({"ID": ID,
                                     "MONEY":0})
        return await get_user(collection, ID)


async def write(collection : motor.AsyncIOMotorCollection, ID: int, money:int):
    """changes ID's balance to money, returns the new user json."""
    user = await collection.find_one_and_update({"ID":ID},{'$set': {'MONEY':money}}, return_document=True, upsert=True)
    return user


async def change(collection : motor.AsyncIOMotorCollection, ID:int, diffrence: float):
    """will change the user with ID's money amount by DIFFRENCE"""
    user = await collection.find_one_and_update({"ID":ID},{'$inc': {'MONEY':diffrence}}, return_document=True, upsert=True)
    return user


class Currency(Cog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.coin_lock = False


    async def on_message(self, message):
        get_money = await get_config_value(self.bot.configs, message.guild.id, 'CURRENCY')
        if get_money:
            await change(self.bot.currency, message.author.id, self.bot.config.MONEY["PER_MESSAGE"])
            await message.add_reaction(self.bot.config.MONEY["REACTION"])
            await asyncio.sleep(1000)
            await message.remove_reaction(self.bot.config.MONEY["REACTION"])

    @commands.command()
    async def wallet(self, ctx, user:discord.User=None):
        if user is None:
            user = ctx.author

        ret = await get_user(self.bot.currency, user.id)
        money = ret["MONEY"]
        return await ctx.send(f"`{user}` has **{money}** Alex Coins")

    @commands.command()
    @commands.is_owner()
    async def write(self,ctx:commands.Context, user:discord.User, amount:int):
        ret = await write(self.bot.currency, user.id, amount)
        return await ctx.send(f"set `{user}`'s coins to {ret['MONEY']}")


def setup(bot):
    bot.add_cog(Currency(bot))
