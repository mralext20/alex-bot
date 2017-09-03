# -*- coding: utf-8 -*-

from discord.ext import commands
from cogs.cog import Cog
import asyncpg
import hashlib

async def query(db: asyncpg.pool.Pool, tag: str, guild: int) -> str:
    ret = await db.fetchval("""SELECT content from tags where name=$1 AND guild=$2""", tag, guild)
    if ret is not None:
        return ret
    else:
        return "can not find that tag."

async def append(db: asyncpg.pool.Pool, tag: str, content: str, author: int, guild: int) -> bool:
    exists = await db.fetchrow("""SELECT name FROM tags WHERE name=$1""", tag)
    if exists:
        return False
    else:
        h = hashlib.sha256(f"{tag}{guild}".encode()).hexdigest()
        await db.execute("""INSERT INTO tags (hash, name, content, author, guild) 
                            VALUES ($1, $2, $3, $4, $5)""", h, tag, content, author, guild)
        return True

async def remove(db: asyncpg.pool.Pool, tag: str, author: int, guild: int) -> bool:
    if await db.fetchrow("""SELECT * FROM tags WHERE author=$1 AND guild=$2 AND name=$3""", author, guild, tag):
        await db.execute("""DROP FROM tags WHERE author=$1 AND guild=$2 AND name=$3""", author, guild, tag)
        return True
    else:
        return False

async def list_tags(db: asyncpg.pool.Pool, guild: int) -> list:
    tags = await db.fetch("""SELECT * FROM tags WHERE guild=$1""", guild)
    return [(tag["name"], tag["author"]) for tag in tags]


class Tags(Cog):
    """The description for Tags goes here."""

    @commands.group(name="tag", invoke_without_command=True)
    async def tags(self, ctx, tag):
        await ctx.send(await query(self.bot.db, tag, ctx.guild.id))

    @tags.command()
    async def create(self, ctx, tag, *, content):
        if await append(self.bot.db, tag, content, ctx.author.id, ctx.guild.id):
            await ctx.send(f"tag {tag} was added to database.")
        else:
            await ctx.send(f"tag {tag} failed to be added \U0001f626")

    @tags.command()
    async def remove(self, ctx, tag):
        if await remove(self.bot.db, tag, ctx.author.id, ctx.guild.id):
            await ctx.send(f"tag '{tag}' removed successfully.")
        else:
            await ctx.send(f"tag was not removed. Are you the owner?")

    @tags.command()
    async def list(self, ctx):
        tags = list(await list_tags(self.bot.db, ctx.guild.id))
        await ctx.send(tags)


def setup(bot):
    bot.add_cog(Tags(bot))
