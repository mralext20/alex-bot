# -*- coding: utf-8 -*-

import datetime
import humanize


import discord
from discord.ext import commands

from ..tools import Cog
DATEFORMAT = "%a, %e %b %Y %H:%M:%S (%-I:%M %p)"


class Utils(Cog):
    """The description for Utils goes here."""
    @commands.command(aliases=['p'])
    async def ping(self, ctx):
        """You know it"""
        start = await ctx.send("Po..")
        assert isinstance(start, discord.Message)
        a = start.created_at
        now = datetime.datetime.utcnow()
        ping = now - a

        await start.edit(content=f"Pong! WS: {ctx.bot.latency * 1000:.2f} ms, rest: {ping.microseconds / 1000:.2f} ms")

    @commands.command()
    async def time(self, ctx):
        """Displays the time in alaska"""
        time = datetime.datetime.now()
        await ctx.send(f'the time in alaska is {time.strftime(DATEFORMAT)}')

    @commands.command()
    async def quote(self, ctx, msg, channel: discord.TextChannel = None):
        """Quotes a message. msg can be message ID or the output of shift clicking the 'copy id' button in the UI."""
        if '-' in msg:
            try:
                channel, msg = [int(i) for i in msg.split('-')]
                channel = self.bot.get_channel(channel)
            except ValueError or discord.errors.NotFound:
                raise commands.BadArgument("your input was not a message id")
        try:

            if channel is None:
                msg = await ctx.channel.fetch_message(msg)
            else:
                msg = await channel.fetch_message(msg)
        except (discord.errors.NotFound, discord.errors.HTTPException):
            return await ctx.send("cant find that message. \N{SLIGHTLY FROWNING FACE}")
        assert isinstance(msg, discord.Message)

        if channel is not None and channel.nsfw and not ctx.channel.nsfw:
            return await ctx.send("Cant send message from NSFW channel in SFW channel")

        ret = discord.Embed(color=discord.Color.blurple())

        if msg.content == "" and msg.attachments == []:
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

    @commands.command(aliases=['diff'])
    async def difference(self, ctx, object_one: int, object_two: int = None):
        """Compares the creation time of two IDs. default to comparing to the current time."""
        one = discord.utils.snowflake_time(object_one)
        if object_two is None:
            object_two = ctx.message.id
        two = discord.utils.snowflake_time(object_two)
        if one > two:
            diff = one - two
        else:
            diff = two - one
        await ctx.send(f'time difference from {one} to {two} is {diff}.')

    @commands.command(name='info', aliases='source about git'.split())
    async def info(self, ctx):
        ret = discord.Embed()
        ret.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)
        ret.add_field(name='Support Server', value='[link](https://discord.gg/jMwPFqp)')
        ret.add_field(name='Source Code', value='[github](https://gitlab.com/mralext20/alex-bot)')
        ret.add_field(name='Servers', value=str(len(self.bot.guilds)))
        ret.add_field(name='Members', value=str(len(list(self.bot.get_all_members()))))
        await ctx.send(embed=ret)

    @commands.command(name='inviteDetails')
    async def inviteDetails(self, ctx, invite: discord.Invite):
        if invite.revoked:
            return await ctx.send("That invite is revoked...")
        ret = discord.Embed()
        ret.add_field(name='aprox members', value=invite.approximate_member_count, inline=True)
        ret.add_field(name='Aprox Present Members', value=invite.approximate_member_count, inline=True)
        ret.add_field(name='guild created at', value=invite.guild.created_at, inline=True)
        ret.add_field(name='guild ID', value=invite.guild.id, inline=True)
        ret.add_field(name='verification level', value=invite.guild.verification_level, inline=True)
        if invit.guild.features != []:
            ret.add_field(name='features:', value=', '.join(invite.guild.features), inline=True)
        ret.add_field(name='inviter name', value=invite.inviter.name, inline=True)
        ret.add_field(name='inviter id', value=invite.inviter.id, inline=True)
        ret.add_field(name='channel target', value=invite.channel.name, inline=True)
        ret.add_field(name='channel Type', value=invite.channel.type, inline=True)


        await ctx.send(embed=ret)



    @commands.command()
    async def invite(self, ctx):
        await ctx.send(f"<{discord.utils.oauth_url(self.bot.user.id)}>")


def setup(bot):
    bot.add_cog(Utils(bot))
