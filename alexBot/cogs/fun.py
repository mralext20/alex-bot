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


def setup(bot):
    bot.add_cog(Fun(bot))
