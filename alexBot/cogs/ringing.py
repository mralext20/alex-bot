import asyncio

import discord
from discord.errors import DiscordException
from discord.ext import commands

from alexBot.classes import RingRate
from alexBot.tools import Cog


class Ringing(Cog):
    @commands.command()
    async def ring(self, ctx: commands.Context, target: discord.Member):
        """Alerts another member of the server that you want someone to talk to. requires that you're in a voice channel."""
        if not ctx.author.voice:
            await ctx.send("cannot ring: you are not in a voice channel")
            return
        if target.voice:
            await ctx.send("cannot ring: they are already in voice")
            return
        if not (await self.bot.db.get_user_data(target.id)).config.ringable:
            await ctx.send("cannot ring: they do not want to be rung")
            return

        ringRate = self.bot.config.ringRates[target.status]
        await ctx.message.add_reaction("❌")
        await self.doRing(ctx.author, target, ctx.channel, ctx.message, ringRate)
        try:
            await ctx.message.clear_reactions()
        except DiscordException:
            pass
        await ctx.message.add_reaction("✅")

    async def doRing(
        self,
        initiator: discord.Member,
        target: discord.Member,
        channel: discord.TextChannel,
        sentinalMessage: discord.Message,
        ringRate: RingRate = RingRate(),
    ):
        times = 0
        while await self.running(target, times, ringRate, sentinalMessage):
            await channel.send(
                f"HELLO, {target.mention}! {initiator.name.upper()} WANTS YOU TO JOIN {initiator.voice.channel.mention}!"
            )
            await asyncio.sleep(ringRate.rate)
            times += 1

    @staticmethod
    async def running(target: discord.Member, times: int, ringRate: RingRate, sentinalMessage: discord.Message):
        if target.voice:
            return False
        if times >= ringRate.times:
            return False

        newSentinalMessage = await sentinalMessage.channel.fetch_message(sentinalMessage.id)

        if not newSentinalMessage.reactions:
            return False
        return newSentinalMessage.reactions[0].count < 2


def setup(bot):
    bot.add_cog(Ringing(bot))
