from alexBot.classes import ReactionRoleConfig
import asyncio
import logging
from typing import Dict

import discord
from discord.ext import commands
from discord.ext.commands.errors import BadArgument
from discord.raw_models import RawReactionActionEvent

from ..tools import Cog

log = logging.getLogger(__name__)


class ReactionRoles(Cog):
    # guild: msg: emoji: role
    cache: Dict[int, Dict[int, Dict[str, int]]] = {}

    @Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        if payload.guild_id not in self.cache:
            await self.load_guild(payload.guild_id)
        try:
            role = self.cache[payload.guild_id][payload.message_id][str(payload.emoji)]
        except KeyError:
            return
        guild = self.bot.get_guild(payload.guild_id)
        role = guild.get_role(role)
        await guild.get_member(payload.user_id).add_roles(role)

    @Cog.listener()
    async def on_raw_reaction_remove(self, payload: RawReactionActionEvent):
        if payload.guild_id not in self.cache:
            await self.load_guild(payload.guild_id)
        try:
            role = self.cache[payload.guild_id][payload.message_id][str(payload.emoji)]
        except KeyError:
            return
        guild = self.bot.get_guild(payload.guild_id)
        role = guild.get_role(role)
        await guild.get_member(payload.user_id).remove_roles(role)

    async def load_guild(self, id: int):
        gd = await self.bot.db.get_guild_data(id)
        reactionRoles = gd.config.reactionRoles
        self.cache[id] = {}
        for rr in reactionRoles:
            self.cache[id][rr.message] = {
                **self.cache[id].get(rr.message, dict()),
                rr.reaction: rr.role,
            }

    @commands.commands()
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.has_guild_permissions(manage_roles=True)
    async def add_reaction_role(self, ctx: commands.Context):
        try:
            await ctx.send("please send a link to the message to be used for reaction roles")
            message = None
            while message is None:
                msg = await self.bot.wait_for(
                    'message',
                    check=(lambda m: m.author == ctx.author and m.channel == ctx.channel),
                    timeout=120,
                )
                try:
                    message = await commands.MessageConverter().convert(ctx, msg.content)
                except BadArgument:
                    await ctx.send("i did not understand that. consider trying the message link.")
            await ctx.send(
                f"great! now, react to that message ( the one in {message.channel.mention}) with the reaction you want for this role."
            )
            emoji = None
            while emoji is None:
                payload = await self.bot.wait_for(
                    'raw_reaction_add',
                    check=(lambda p: p.message_id == message.id and p.user_id == ctx.author.id),
                    timeout=120,
                )
                emoji = str(payload.emoji)
            await ctx.send(
                "awesome! now, what role does this emoji, {emoji}, corispond to? send the ID, name or a mention."
            )
            role = None
            while role is None:
                msg = await self.bot.wait_for(
                    'message',
                    check=(lambda m: m.author == ctx.author and m.channel == ctx.channel),
                    timeout=120,
                )
                try:
                    role = await commands.RoleConverter().convert(ctx, msg.content)
                except BadArgument:
                    await ctx.send("i did not understand that. perhaps try the role ID?")
            rr = ReactionRoleConfig(message.id, role.id, emoji)
            gd = await self.bot.db.get_guild_data(ctx.guild.id)
            gd.config.reactionRoles.append(rr)
            await self.bot.db.save_guild_data(ctx.guild.id, gd)
            await self.load_guild(ctx.guild.id)
            await ctx.send(
                f"setup the reaction role for {role.name} as the emoji {emoji} in {message.channel.mention}, at message {message.jump_url}."
            )
        except asyncio.TimeoutError:
            await ctx.send("timed out.")

    @commands.commands()
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.has_guild_permissions(manage_roles=True)
    async def remove_reaction_role(self, ctx: commands.Context):
        gd = await self.bot.db.get_guild_data(ctx.guild.id)
        rrs = gd.config.reactionRoles
        if not rrs:
            await ctx.send("you don't have any reaction roles setup!")
        for rr in rrs:
            embed = discord.Embed()
            embed.add_field("emoji", value=rr.reaction)
            embed.add_field("role", value=ctx.guild.get_role(rr.role))
            msg = await ctx.send("is this the set you want to remove? (`yes` or anything else)", embed=embed)
            t = await self.bot.wait_for(
                'message',
                check=(lambda m: m.author == ctx.author and m.channel == ctx.channel),
                timeout=120,
            )
            if t.content == "yes":
                rrs.remove(rr)
                await self.bot.db.save_guild_data(ctx.guild.id, gd)
                await ctx.send("i've successfully removed that reaction roles")
                await self.load_guild(ctx.guild.id)
                return
            else:
                continue
        await ctx.send("you didn't remove any reaction roles.")


def setup(bot):
    bot.add_cog(ReactionRoles(bot))
