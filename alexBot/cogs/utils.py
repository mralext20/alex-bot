# -*- coding: utf-8 -*-

import asyncio
import datetime
import random
from dataclasses import dataclass
from typing import List, Optional

import discord
import humanize
from discord import app_commands
from discord.ext import commands
from discord.member import VoiceState

from ..tools import Cog

DATEFORMAT = "%a, %e %b %Y %H:%M:%S (%-I:%M %p)"


@dataclass
class Roll:
    dice: str
    rolls: List[int]

    def __str__(self):
        return f"{self.dice}: {', '.join([str(r) for r in self.rolls])}"


class Utils(Cog):
    @app_commands.command()
    @app_commands.describe(dice="dice format in XdY. can be multiple sets, seperated by spaces")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def roll(self, interaction: discord.Interaction, dice: str):
        """Rolls a dice in NdN format."""
        roll_results: List[Roll] = []
        for rollset in dice.split(" "):
            try:
                rolls, limit = map(int, rollset.split("d"))
                if rolls > 100:
                    return await interaction.response.send_message(
                        "You can't roll more than 100 dice at once!", ephemeral=True
                    )
            except (TypeError
                    , ValueError
                    , discord.HTTPException
                    , discord.InteractionResponded):
                return await interaction.response.send_message("Format has to be in `WdX YdZ`...!", ephemeral=True)
            roll_results.append(Roll(f"{rolls}d{limit}", [random.randint(1, limit) for r in range(rolls)]))

        result = "\n".join([str(r) for r in roll_results])
        raw_results = []
        for roll in roll_results:
            [raw_results.append(r) for r in roll.rolls]

        result += f"\n\nTotal: {sum(raw_results)}"
        result += f"\nAverage: {sum(raw_results) / len(raw_results)}"
        result += f"\nMax: {max(raw_results)}"
        result += f"\nMin: {min(raw_results)}"
        try:
            await interaction.response.send_message(result, ephemeral=False)
        except discord.HTTPException:
            await interaction.response.send_message("Result too long!", ephemeral=True)

    @commands.command(aliases=['diff'])
    async def difference(self, ctx: commands.Context, one: discord.Object, two: Optional[discord.Object] = None):
        """Compares the creation time of two IDs. default to comparing to the current time."""
        two = two or ctx.message
        if two is None:
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
        ret.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar.url)
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
        ret.set_thumbnail(url=invite.guild.icon.url)
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


async def setup(bot):
    await bot.add_cog(Utils(bot))
