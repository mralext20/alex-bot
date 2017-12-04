from discord.ext import commands

from tools import Cog
from tools import getGuildConfig




class Configs(Cog):
    """handels guild config settings"""
    @commands.group(name="config", invoke_without_command=True)
    async def config(self, ctx: commands.Context):
        """how you configure your guild"""
        await ctx.send((await self.bot.formatter.format_help_for(ctx, ctx.command))[0])

    @config.command()
    async def get(self, ctx, key):
        """gets the value of a key"""
        #await getGuildConfigKey(pool, ctx.guild.id, key):
        pass
    @config.command()
    async def set(self, ctx, key, value):
        """sets the value of a key"""
        pass

    @config.command()
    async def list(self,ctx):
        """lists the available config keys"""
        cfg = await getGuildConfig(self.bot.pool, ctx.guild.id)
        ret = f'your guild config:  ```json\n{cfg[0]}```'
        await ctx.send(ret)


def setup(bot):
    bot.add_cog(Configs(bot))
