import asyncio
import typing
import discord
from discord.errors import DiscordException

from alexBot.tools import Cog, get_user_config
from discord.ext import commands


class Ringing(Cog):
    @commands.command()
    async def ring(self, ctx: commands.Context, target: discord.Member):
        # if not ctx.author.voice:
        #     await ctx.send("cannot ring: you are not in a voice channel")
        #     return
        if target.voice:
            await ctx.send("cannot ring: they are already in voice")
            return
        if not (await get_user_config(self.bot, target.id))["ringable"]:
            await ctx.send("cannot ring: they do not want to be rung")
            return

        ringRate = self.bot.config.ringRates[target.status]
        await ctx.message.add_reaction("❌")
        await self.doRing(ctx.author.name, target, ctx.channel, ctx.message, ringRate)
        await ctx.message.remove_reaction("❌", self.bot.user)
        try:
            await ctx.message.clear_reactions()
        except DiscordException:
            pass
        await ctx.message.add_reaction("✅")

    @staticmethod
    async def doRing(initiator: str,
                     target: discord.Member,
                     channel: discord.TextChannel,
                     sentinalMessage: discord.Message,
                     ringRate={"times": 1, "rate": 1},
                     ):
        times = 0
        while (not target.voice) and times < ringRate['times'] and ((await sentinalMessage.channel.fetch_message(sentinalMessage.id)).reactions[0].count < 2):
            await channel.send(f"HELLO, {target.mention}! {initiator.upper()} WANTS YOU TO JOIN VOICE!")
            await asyncio.sleep(ringRate['rate'])
            times += 1


def setup(bot):
    bot.add_cog(Ringing(bot))
