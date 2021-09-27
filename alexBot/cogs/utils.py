# -*- coding: utf-8 -*-

import datetime
from typing import Optional

import discord
from discord.member import VoiceState
import humanize
from discord.ext import commands

from ..tools import Cog, ObjectConverter

DATEFORMAT = "%a, %e %b %Y %H:%M:%S (%-I:%M %p)"


class Utils(Cog):
    @commands.command()
    async def time(self, ctx: commands.Context):
        """Displays the time in alaska"""
        time = datetime.datetime.now()
        await ctx.send(f'the time in alaska is {time.strftime(DATEFORMAT)}')

    @commands.command(aliases=['diff'])
    async def difference(self, ctx: commands.Context, one: ObjectConverter, two: ObjectConverter = None):
        """Compares the creation time of two IDs. default to comparing to the current time."""
        if two is None:
            now = True
            two = ctx.message
        else:
            now = False
        if one.created_at > two.created_at:
            earlier_first = False
            diff = one.created_at.replace(tzinfo=datetime.timezone.utc) - two.created_at.replace(
                tzinfo=datetime.timezone.utc
            )
        else:
            earlier_first = True
            diff = two.created_at.replace(tzinfo=datetime.timezone.utc) - one.created_at.replace(
                tzinfo=datetime.timezone.utc
            )

        embed = discord.Embed()
        embed.add_field(
            name=f"{'Earlier' if earlier_first else 'Later'} (`{one.id}`)",
            value=f"`{one.created_at.replace(tzinfo=datetime.timezone.utc)}`, <t:{one.created_at.replace(tzinfo=datetime.timezone.utc).timestamp():.0f}> - <t:{one.created_at.replace(tzinfo=datetime.timezone.utc).timestamp():.0f}:R>",
        )
        embed.add_field(
            name=f"{'Later' if earlier_first else 'Earlier'} (`{two.id}`)",
            value=f"`{two.created_at.replace(tzinfo=datetime.timezone.utc)}`, <t:{two.created_at.replace(tzinfo=datetime.timezone.utc).timestamp():.0f}> -  <t:{two.created_at.replace(tzinfo=datetime.timezone.utc).timestamp():.0f}:R>",
        )
        embed.add_field(name="Difference", value=f"`{diff}` ({humanize.naturaldelta(diff)})")

        await ctx.send(embed=embed)

    @commands.command(name='info', aliases='source about git'.split())
    async def info(self, ctx):
        """general bot information"""
        ret = discord.Embed()
        ret.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)
        ret.add_field(name='Support Server', value='[link](https://discord.gg/jMwPFqp)')
        ret.add_field(name='Source Code', value='[github](https://github.com/mralext20/alex-bot)')
        ret.add_field(name='Servers', value=str(len(self.bot.guilds)))
        ret.add_field(name='Members', value=str(len(list(self.bot.get_all_members()))))
        await ctx.send(embed=ret)

    @commands.command(name='inviteDetails')
    async def inviteDetails(self, ctx, invite: discord.Invite):
        """Tells you about an invite, such as how many members the server it's pointed to has and more!"""
        if invite.revoked:
            return await ctx.send("That invite is revoked...")
        ret = discord.Embed()
        ret.set_thumbnail(url=invite.guild.icon_url)
        ret.title = invite.guild.name
        ret.add_field(name='aprox members', value=invite.approximate_member_count, inline=True)
        ret.add_field(name='Aprox Present Members', value=invite.approximate_presence_count, inline=True)
        ret.add_field(name='guild created at', value=invite.guild.created_at, inline=True)
        ret.add_field(name='guild ID', value=invite.guild.id, inline=True)
        ret.add_field(name='verification level', value=invite.guild.verification_level, inline=True)
        if invite.guild.features:
            ret.add_field(name='features:', value=', '.join(invite.guild.features), inline=False)
        if invite.inviter:
            ret.add_field(name='inviter name', value=invite.inviter.name, inline=True)
            ret.add_field(name='inviter id', value=invite.inviter.id, inline=True)
        if invite.channel:
            ret.add_field(name='channel target', value=invite.channel.name, inline=True)
            ret.add_field(name='channel Type', value=invite.channel.type, inline=True)

        await ctx.send(embed=ret)

    @commands.command()
    async def invite(self, ctx):
        """tells you my invite link!"""
        await ctx.send(
            f"<https://discord.com/oauth2/authorize?client_id={self.bot.user.id}&scope=bot%20applications.commands>"
        )

    @commands.command()
    @commands.has_guild_permissions(move_members=True)
    @commands.bot_has_guild_permissions(move_members=True)
    async def voice_move(self, ctx: commands.Context, target: discord.VoiceChannel):
        if not ctx.author.voice:
            raise ValueError("you must be in a voice call!")
        for user in ctx.author.voice.channel.members:
            ctx.bot.loop.create_task(user.move_to(target, reason=f"as requested by {ctx.author}"))
        await ctx.send(":ok_hand:")

    @Cog.listener()
    async def on_voice_state_update(self, member, before: Optional[VoiceState], after: Optional[VoiceState]):
        if after is None:
            return
        if after.channel.id == 889031486978785312:
            # check for existing instance and close
            if not after.channel.guild.voice_client:
                vc = await after.channel.connect()
                vc.play(
                    discord.PCMVolumeTransformer(discord.FFmpegPCMAudio("https://retail-music.com/walmart_radio.mp3"))
                )


def setup(bot):
    bot.add_cog(Utils(bot))
