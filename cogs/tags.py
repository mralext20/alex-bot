# -*- coding: utf-8 -*-
import discord
from discord.ext import commands
from cogs.cog import Cog
import motor.motor_asyncio as motor
import hashlib

motorCollection = motor.AsyncIOMotorCollection

async def query(collection: motorCollection, tag: str,guild: int) -> str:
    ret = await collection.find_one({"NAME": tag, "GUILD": guild})
    if ret is not None:
        return ret["CONTENT"]
    else:
        return "can not find that tag"

async def append(collection: motorCollection, tag: str, content: str, author: int, guild:int ) -> bool:
    h = hashlib.sha256(f"{tag}{guild}".encode()).hexdigest()
    if await collection.find_one({"HASH": h}):
        return False
    else:
        await collection.insert_one({"NAME"   : tag,
                                     "CONTENT": content,
                                     "AUTHOR" : author,
                                     "GUILD"  : guild,
                                     "HASH"   : h
                                     })
        return True


async def list_tags(collection: motorCollection, guild: int) -> list:
    cur = collection.find({"GUILD": guild})
    tags = await cur.to_list(20)
    return tags


class Tags(Cog):
    """The description for Tags goes here."""

    @commands.group(name="tag", invoke_without_command=True)
    @commands.guild_only()
    async def tags(self, ctx, tag):
        await ctx.send(await query(self.bot.tagsDB, tag, ctx.guild.id))

    @tags.command()
    @commands.guild_only()
    async def create(self, ctx, tag, *, content):
        """Creates a tag"""
        try:
            assert len(tag) < len(content)
        except AssertionError:
            await ctx.send(f"failed to add tag {tag} to the database. content needs to be shorter than your tag name. <:lumaslime:340673841858740224>")
            return
        if await append(self.bot.tagsDB, tag, content, ctx.author.id, ctx.guild.id):
            await ctx.send(f"tag {tag} was added to database.")
        else:
            await ctx.send(f"tag {tag} failed to be added \U0001f626")

    @tags.command()
    @commands.guild_only()
    async def remove(self, ctx, tag):
        """Removes a tag"""
        if await remove(self.bot.tagsDB, tag, ctx.author.id, ctx.guild.id):
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
