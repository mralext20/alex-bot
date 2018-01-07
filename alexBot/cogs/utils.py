# -*- coding: utf-8 -*-

import datetime
import humanize


import discord
from discord.ext import commands

from ..tools import Cog
DATEFORMAT = "%a, %e %b %Y %H:%M:%S (%-I:%M %p)"


class Utils(Cog):
    """The description for Utils goes here."""
    @commands.command()
    async def ping(self, ctx):
        """You know it"""
        start = await ctx.send("Po..")
        assert isinstance(start, discord.Message)
        a = start.created_at
        now = datetime.datetime.utcnow()
        ping = now - a

        await start.edit(content=f"Pong! WS: {ctx.bot.latency * 1000:.2f} ms, rest: {ping.microseconds / 1000:.2f} ms")

    @commands.command()
    async def time(self,ctx):
        """Displays the time in alaska"""
        time = datetime.datetime.now()
        bostonTime = time + datetime.timedelta(hours=4)
        await ctx.send(f'the time in alaska is {time.strftime(DATEFORMAT)}')


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

    @commands.command()
    async def difference(self, ctx, object_one:int, object_two:int=None):
        """compares the creation of two discord IDs. interprets a mising second arg as the current ID."""
        one = discord.utils.snowflake_time(object_one)
        if object_two==None:
            object_two = ctx.message.id
        two = discord.utils.snowflake_time(object_two)
        if one > two:
            diff = two - one
        else:
            diff = one - two
        diff = humanize.naturaldelta(diff)
        one = humanize.naturaldate(one)
        two = humanize.naturaldate(two)
        await ctx.send(f'time difference from {one} to {two} is {diff}.')


    @commands.command(name='info', aliases='source about git'.split())
    async def info(self, ctx):
        ret = discord.Embed()
        ret.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)
        ret.add_field(name='Support Server', value='[link](https://discord.gg/jMwPFqp)')
        ret.add_field(name='Source Code', value='[github](https://github.com/mralext20/alex-bot/)')
        ret.add_field(name='Guilds', value=str(len(self.bot.guilds)))
        await ctx.send(embed=ret)

    @commands.command()
    @commands.is_owner()
    async def reloadadmin(self, ctx):
        """Reload the admin cog"""
        try:
            self.bot.unload_extension("alexBot.cogs.admin")
            self.bot.load_extension("alexBot.cogs.admin")
        except Exception as e:
            await ctx.send(f'**`ERROR:`** {type(e).__name__} - {e}')
        else:
            await ctx.send('**`SUCCESS`**')


def setup(bot):
    bot.add_cog(Utils(bot))


