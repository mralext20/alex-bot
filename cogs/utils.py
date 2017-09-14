# -*- coding: utf-8 -*-

from discord.ext import commands
import datetime
from cogs.cog import Cog
import discord

class Utils(Cog):
    """The description for Utils goes here."""


    @commands.command(name='reload', hidden=True)
    @commands.is_owner()
    async def cog_reload(self, ctx, *, cog: str):
        """Command which Reloads a Module.
        Remember to use dot path. e.g: cogs.owner"""
        if cog == "cogs.utils":
            ctx.send("im sorry, i cant reload myself for safety reasons.")
            return
        try:
            self.bot.unload_extension(cog)
            self.bot.load_extension(cog)
        except Exception as e:
            await ctx.send(f'**`ERROR:`** {type(e).__name__} - {e}')
        else:
            await ctx.send('**`SUCCESS`**')


    @commands.command()
    async def ping(self, ctx):
        await ctx.send(f"Pong! time is {ctx.bot.latency * 1000:.2f} ms")

    @commands.command()
    async def time(self,ctx):
        time = datetime.datetime.now().strftime("%a, %e %b %Y %H:%M:%S (%-I:%M %p)")
        await ctx.send(f'the time in alaska is {time}')


    @commands.command()
    async def quote(self, ctx, msg:int, channel: discord.TextChannel=None):
        if channel is not None:
            msg = await channel.get_message(msg)
        else:
            msg = await ctx.channel.get_message(msg)

        assert isinstance(msg, discord.Message)

        ret = discord.Embed(color=discord.Color.blurple())
        ret.description = msg.content
        ret.set_author(name=msg.author.name, icon_url=msg.author.avatar_url)
        ret.timestamp = msg.created_at
        try:
            ret.set_image(url=msg.attachments[0].url)
        except IndexError:
            try:
                ret.set_image(url=msg.embeds[0].thumbnail.url)
            except IndexError:
                pass

        # TODO: format the timedelta better. less microseconds.
        ret.set_footer(text=f"Quoted message is {ctx.message.created_at - ret.timestamp} old, from ")

        await ctx.send(embed=ret)


def setup(bot):
    bot.add_cog(Utils(bot))


