import logging
import re
import time
from typing import Dict

import discord
from discord.ext import commands

from ..tools import Cog, get_json

log = logging.getLogger(__name__)
ayygen = re.compile("[aA][yY][Yy][yY]*")


class Fun(Cog):
    last_posted: Dict[int, float] = {}

    @commands.command()
    async def cat(self, ctx: commands.Context):
        """Posts a pretty photo of a cat"""
        cat = await get_json(
            self.bot.session,
            f"https://thecatapi.com/api/images/get?format=json" f"&api_key={self.bot.config.cat_token}",
        )
        cat = cat[0]
        embed = discord.Embed()
        embed.set_image(url=cat["url"])
        embed.url = "http://thecatapi.com"
        embed.title = "cat provided by the cat API"
        await ctx.send(embed=embed)

    @commands.command()
    async def dog(self, ctx: commands.Context):
        """Posts a pretty picture of a dog."""
        dog = None
        while dog is None or dog["url"][-3:].lower() == "mp4":
            dog = await get_json(self.bot.session, "https://random.dog/woof.json")
            log.debug(dog["url"])
        ret = discord.Embed()
        ret.set_image(url=dog["url"])
        await ctx.send(embed=ret)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if self.bot.location == "dev" or message.guild is None:
            return
        cfg = (await self.bot.db.get_guild_data(message.guild.id)).config
        if cfg.ayy:
            if ayygen.fullmatch(message.content):
                await message.reply("lmao", mention_author=False)
        if cfg.veryCool:
            if message.content.lower().startswith("thank you "):
                await message.reply("very cool", mention_author=False)
        if cfg.firstAmendment:
            if any([check in message.content.lower() for check in ["free speech", "first amendment"]]):
                if self.last_posted.get(message.channel.id, time.time() - 60 * 60 * 24) < time.time() - 60 * 5:
                    await message.reply("https://xkcd.com/1357/", mention_author=True)
                    self.last_posted[message.channel.id] = time.time()
        # bespoke thing, maybe make config and guild based in the future
        if message.channel.id == 847555306166943755:
            if '?' != message.content[-1]:
                await message.delete()
            await message.add_reaction("<:greentick:567088336166977536>")
            await message.add_reaction("<:redtick:567088349484023818>")


def setup(bot):
    bot.add_cog(Fun(bot))
