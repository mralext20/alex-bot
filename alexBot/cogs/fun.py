import logging
import re
from discord.ext import commands
from ..tools import Cog
from ..tools import get_guild_config
from ..tools import get_json, get_xml
import discord

log = logging.getLogger(__name__)
ayygen = re.compile('[aA][yY][Yy][yY]*')


class Fun(Cog):
    @commands.command()
    async def cat(self, ctx):
        cat = await get_xml(self.bot.session, f"https://thecatapi.com/api/images/get?format=xml"
                                              f"&api_key={self.bot.config.cat_token}")
        cat = cat['response']['data']['images']['image']
        embed = discord.Embed()
        embed.set_image(url=cat['url'])
        embed.url = cat['source_url']
        embed.title = "cat provided by the cat API"
        await ctx.send(embed=embed)

    @commands.command()
    async def dog(self, ctx):
        dog = None
        while dog is None or dog['url'][-3:].lower() == 'mp4':
            dog = await get_json(self.bot.session, 'https://random.dog/woof.json')
            log.debug(dog['url'])
        ret = discord.Embed()
        ret.set_image(url=dog['url'])
        await ctx.send(embed=ret)

    async def on_message(self, message):
        if self.bot.location == 'dev' or message.guild is None:
            return
        if (await get_guild_config(self.bot, message.guild.id))['ayy'] is False:
            return

        if ayygen.fullmatch(message.content):
            await message.channel.send("lmao")


def setup(bot):
    bot.add_cog(Fun(bot))
