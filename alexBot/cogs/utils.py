# -*- coding: utf-8 -*-

import datetime

import discord
import humanize
from discord.ext import commands

from ..tools import Cog


class Utils(Cog):
    """The description for Utils goes here."""


    @commands.command(name='reload', hidden=True)
    @commands.is_owner()
    async def cog_reload(self, ctx, *, cog: str):
        """Command which Reloads a Module."""
        if cog == "utils":
            await ctx.send("im sorry, i cant reload myself for safety reasons.")
            return
        try:
            self.bot.unload_extension(f"alexBot.cogs.{cog}")
            self.bot.load_extension(f"alexBot.cogs.{cog}")
        except Exception as e:
            await ctx.send(f'**`ERROR:`** {type(e).__name__} - {e}')
        else:
            await ctx.send('**`SUCCESS`**')


    @commands.command()
    async def ping(self, ctx):
        """You know it"""
        await ctx.send(f"Pong! time is {ctx.bot.latency * 1000:.2f} ms")

    @commands.command()
    async def time(self,ctx):
        """Displays the time in alaska"""
        time = datetime.datetime.now().strftime("%a, %e %b %Y %H:%M:%S (%-I:%M %p)")
        await ctx.send(f'the time in alaska is {time}')


    @commands.command()
    async def quote(self, ctx, msg:int, channel: discord.TextChannel=None):
        """Quotes a message"""
        try:
            if channel is not None:
                msg = await channel.get_message(msg)
            else:
                msg = await ctx.channel.get_message(msg)
        except discord.errors.NotFound:
            await ctx.send("cant find that message. \N{SLIGHTLY FROWNING FACE}")
        assert isinstance(msg, discord.Message)

        ret = discord.Embed(color=discord.Color.blurple())

        if msg.content is "" and msg.attachments == []:
            embed = msg.embeds[0]
            try:
                assert isinstance(embed, discord.Embed)
            except AssertionError:
                return
            ret = embed
        else:
            ret.description = msg.content

            # handle images, and images attached with URLs
            try:
                ret.set_image(url=msg.attachments[0].url)
            except IndexError:
                try:
                    ret.set_image(url=msg.embeds[0].thumbnail.url)
                except IndexError:
                    pass

        ret.timestamp = msg.created_at
        ret.set_author(name=msg.author.name, icon_url=msg.author.avatar_url)
        age = ctx.message.created_at - ret.timestamp
        age = humanize.naturaldelta(age)

        ret.set_footer(text=f"Quoted message is {age} old, from ")

        await ctx.send(embed=ret)


def setup(bot):
    bot.add_cog(Utils(bot))


