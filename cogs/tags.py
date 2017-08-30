# -*- coding: utf-8 -*-

from discord.ext import commands
from cogs.cog import Cog
import pickle

from config import tagdb

def query(tag:str):
    with open(tagdb,"rb") as f:
        tags = pickle.load(f)
    try:
        return tags[tag]
    except KeyError:
        return "can not find that tag."

def append(tag:str, content:str) -> bool:
    with open(tagdb, "rb") as f:
        tags = pickle.load(f)
    if tag in tags:
        return False
    else:
        with open(tagdb, 'wb') as f:
            tags[tag] = content
            pickle.dump(tags,f)
            return True

def remove(tag:str) -> bool:
    with open(tagdb, "rb") as f:
        tags = pickle.load(f)
    if tag in tags:
        with open(tagdb, 'wb') as f:
            del tags[tag]
            pickle.dump(tags, f)
            return True
    else:
        return False

def list_tags():
    with open(tagdb, "rb") as f:
        tags = pickle.load(f)
    return tags.keys()

class Tags(Cog):
    """The description for Tags goes here."""

    @commands.group(name="tags", invoke_without_command=True)
    async def tag(self, ctx, tag):
        await ctx.send(query(tag))


    @tag.command()
    async def create(self, ctx, tag, *, content):
        if append(tag, content):
            await ctx.send(f"tag {tag} was added to database.")
        else:
            await ctx.send(f"tag {tag} failed to be added \U0001f626")


    @tag.command()
    async def remove(self,ctx, tag):
        if remove(tag):
            await ctx.send(f"tag '{tag}' removed sucessfully.")
        else:
            await ctx.send(f"tag was not removed.")

    @tag.command()
    async def list(self, ctx):
        tags = list(list_tags())


        await ctx.send(tags)


def setup(bot):
    bot.add_cog(Tags(bot))
