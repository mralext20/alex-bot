
from discord.ext import commands

from ..tools import Cog
from ..tools import get_json


import discord



class Fun(Cog):

    @commands.command()
    async def cat(self, ctx):
        cat = await get_json(self.bot.session,'http://random.cat/meow')
        ret = discord.Embed()
        ret.set_image(url=cat['file'])
        await ctx.send(embed=ret)

    @commands.command()
    async def dog(self,ctx):
        dog = await get_json(self.bot.session, 'https://random.dog/woof.json')
        ret = discord.Embed()
        ret.set_image(url=dog['url'])
        await ctx.send(embed=ret)


    async def on_message(self, message):
        if self.bot.prefix is 'alex' or message.guild is None:
            return
        ayygen = ('ayy' + 'y' * x for x in range(20))
        if message.content in ayygen:
            await message.channel.send("lmao")


def setup(bot):
    bot.add_cog(Fun(bot))
