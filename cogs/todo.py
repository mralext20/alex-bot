# -*- coding: utf-8 -*-
import discord
from discord.ext import commands
from cogs.cog import Cog
import asyncpg
import hashlib

async def query(db: asyncpg.pool.Pool, todo: str, author: int) -> str:
    ret = await db.fetchval("""SELECT content from todo where name=$1 AND author=$2""", todo, author)
    if ret is not None:
        return ret
    else:
        return "can not find that todo."

async def append(db: asyncpg.pool.Pool, todo: str, content: str, author: int) -> bool:
    exists = await db.fetchrow("""SELECT name FROM todo WHERE name=$1""", todo)
    if exists:
        return False
    else:
        h = hashlib.sha256(f"{todo}{author}".encode()).hexdigest()
        await db.execute("""INSERT INTO todo (hash, name, content, author) 
                            VALUES ($1, $2, $3, $4)""", h, todo, content, author)
        return True


async def remove(db: asyncpg.pool.Pool, todo: str, author: int) -> bool:
    if await db.fetchrow("""SELECT * FROM todo WHERE author=$1 AND name=$2""", author, todo):
        await db.execute("""DELETE FROM todo WHERE author=$1 AND name=$2""", author, todo)
        return True
    else:
        return False


async def list_todos(db: asyncpg.pool.Pool, author: int) -> list:
    todos = await db.fetch("""SELECT * FROM todo WHERE author=$1""", author)
    return [(todo["name"], todo["content"]) for todo in todos]


class Todo(Cog):
    """The description for Todo goes here."""

    @commands.group(name="todo", invoke_without_command=True)
    async def todo(self, ctx, todo):
        await ctx.send(await query(self.bot.db, todo, ctx.author.id))

    @todo.command()
    async def create(self, ctx, todo, *, content:str="<no content>"):
        if await append(self.bot.db, todo, content, ctx.author.id):
            await ctx.send(f"{todo} was added to the todo list.")
        else:
            await ctx.send(f"todo `{todo}` failed to be added \U0001f626")

    @todo.command()
    async def remove(self, ctx, todo):
        if await remove(self.bot.db, todo, ctx.author.id):
            await ctx.send(f"todo '{todo}' removed successfully.")
        else:
            await ctx.send(f"{todo} was not removed. did that entire exist?")

    @todo.command()
    async def list(self, ctx):
        todo = list(await list_todos(self.bot.db, ctx.author.id)) 
        todo = [(todo[0], todo[1][0:40]) for todo in todo]
        todo = discord.Embed(description=str(todo))
        await ctx.send(embed=todo)


def setup(bot):
    bot.add_cog(Todo(bot))
