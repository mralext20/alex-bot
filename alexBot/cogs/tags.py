# -*- coding: utf-8 -*-
import hashlib

import discord
from asyncpg.pool import Pool
from asyncpg import UniqueViolationError
from discord.ext import commands

from ..tools import Cog


def get_hash(tag:str, guild:int) -> str:
    return hashlib.sha256(f"{tag}{guild}".encode()).hexdigest()

async def query(pool:Pool, tag: str, guild:int):
    ret = await pool.execute("""SELECT (content, author, guild, hash) 
                                FROM tags WHERE GUILD=$1 AND TAG=$2""", guild, tag)
    if ret is not None:
        return ret
    else:
        raise commands.BadArgument(f"{tag} not found")


async def append(pool: Pool, tag: str, content: str, author: int, guild: int) -> None:
    """creates a tag. raises commands.BadArgument when fails."""
    h = get_hash(tag, guild)
    try:
        await pool.execute("""INSERT INTO tags (tag, content, author, guild, hash) VALUES
                              ($1,$2,$3,$4,$5)""",tag,content,author,guild,h)
    except UniqueViolationError:
        raise commands.BadArgument("Tag exists")


async def list_tags(pool:Pool, guild: int, author:int=None) -> list:
    if author is None:
        ret = await pool.fetch("""SELECT (tag, content, author) FROM tags 
        WHERE guild=$1""",guild)
    else:
        ret = await pool.fetch("""SELECT (tag, content, author) FROM tags 
        WHERE guild=$1 AND author=$2""", guild, author)
    return ret


async def remove(db: Pool, tag: str, author: int, guild: int) -> None:
    h = get_hash(tag,guild)
    if await db.fetchrow("""SELECT * FROM tags WHERE author=$1 AND hash=$2""", author, h):
        await db.execute("""DROP FROM tags WHERE author=$1 AND hash=$2""", author, h)
    else:
        raise commands.MissingPermissions("you are not the owner of that tag")


class Tags(Cog):
    """commands relating to the tags functionality of the bot."""

    @commands.group(name="tag", invoke_without_command=True)
    @commands.guild_only()
    async def tags(self, ctx, tag):
        await ctx.send(await query(self.bot.pool, tag, ctx.guild.id))

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
        if await remove(self.bot.pool, tag, ctx.author.id, ctx.guild.id):
            await ctx.send(f"tag '{tag}' removed successfully.")
        else:
            await ctx.send(f"tag was not removed. Are you the owner?")

    @tags.command()
    @commands.guild_only()
    async def list(self, ctx):
        """Lists all the tags for this guild"""
        tags = list(await list_tags(self.bot.tagsDB, ctx.guild.id))
        ret = ""
        for tag in tags:
            ret = ret + f"{tag['NAME']}, created by <@{tag['AUTHOR']}>\n"
        embed = discord.Embed()
        embed.description = ret
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Tags(bot))
