# -*- coding: utf-8 -*-
import hashlib

import discord
from asyncpg.pool import Pool
from asyncpg import UniqueViolationError
from discord.ext import commands

from collections import namedtuple
from typing import List


from ..tools import Cog


def get_hash(tag: str, guild: int) -> str:
    return hashlib.sha256(f"{tag}{guild}".encode()).hexdigest()


Tag = namedtuple('Tag', ["tag", "content", "author"])


async def query(pool: Pool, tag: str, guild: int) -> Tag:
    h = get_hash(tag, guild)
    ret = await pool.fetchrow("""SELECT (content, author, guild, hash)
                                FROM tags WHERE hash=$1""", h)
    if ret is not None:
        ret = ret[0]
        return Tag(tag, ret[0], ret[1])
    else:
        raise commands.BadArgument(f"{tag} not found")


async def append(pool: Pool, tag: str, content: str, author: int, guild: int) -> None:
    """creates a tag. raises commands.BadArgument when fails."""
    h = get_hash(tag, guild)
    try:
        await pool.execute("""INSERT INTO tags (tag, content, author, guild, hash) VALUES
                              ($1,$2,$3,$4,$5)""", tag, content, author, guild, h)
    except UniqueViolationError:
        raise commands.BadArgument("Tag exists")


async def list_tags(pool: Pool, guild: int, author: int = None) -> List[Tag]:
    ret = []
    if author is None:
        tags = await pool.fetch("""SELECT (tag, content, author) FROM tags
        WHERE guild=$1""", guild)
    else:
        tags = await pool.fetch("""SELECT (tag, content, author) FROM tags
        WHERE guild=$1 AND author=$2""", guild, author)

    for record in tags:
        record = record[0]
        ret.append(Tag(record[0], record[1], record[2]))
    return ret


async def remove(db: Pool, tag: str, author: int, guild: int) -> None:
    h = get_hash(tag, guild)
    ret = await db.execute("""DELETE FROM tags WHERE author=$1 AND hash=$2""", author, h)
    if ret == "DELETE 1":
        return
    else:
        raise commands.BadArgument("you are not the owner of that tag, or it does not exist.")


class Tags(Cog):
    """commands relating to the tags functionality of the bot."""

    @commands.group(name="tag", invoke_without_command=True)
    @commands.guild_only()
    async def tags(self, ctx, tag):
        tag = await query(self.bot.pool, tag, ctx.guild.id)
        await ctx.send(tag.content)

    @tags.command()
    @commands.guild_only()
    async def create(self, ctx, tag, *, content):
        """Creates a tag"""
        try:
            assert len(tag) < len(content)
        except AssertionError:
            await ctx.send(f"failed to add tag {tag} to the database. content needs to be shorter than your tag name."
                           f" <:lumaslime:340673841858740224>")
            return
        await append(self.bot.pool, tag, content, ctx.author.id, ctx.guild.id)
        await ctx.send(f"tag {tag} was added to database.")

    @tags.command()
    @commands.guild_only()
    async def remove(self, ctx, tag):
        """Removes a tag"""
        await remove(self.bot.pool, tag, ctx.author.id, ctx.guild.id)
        await ctx.send(f"tag '{tag}' removed successfully.")

    @tags.command()
    @commands.guild_only()
    async def info(self, ctx, tag):
        tag = await query(self.bot.pool, tag, ctx.guild.id)
        author = self.bot.get_user(tag.author)
        ret = discord.Embed()
        ret.set_author(name=author.name, icon_url=author.avatar_url)
        ret.add_field(name="Name", value=tag.tag, inline=True)
        await ctx.send(embed=ret)

    @tags.command()
    @commands.guild_only()
    async def list(self, ctx):
        """Lists all the tags for this guild"""
        tags = list(await list_tags(self.bot.pool, ctx.guild.id))
        ret = ""
        for tag in tags:
            if len(ret) > 1000:
                ret += "\n\n cut output due to length"
                break
            ret = ret + f"{tag.tag}, created by <@{tag.author}>\n"
        embed = discord.Embed()
        embed.description = ret
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Tags(bot))
