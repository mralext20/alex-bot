from discord.ext import commands

from tools import Cog
from tools import get_guild_config


class Configs(Cog):
    """handels guild config settings"""
    @commands.group(name="config", invoke_without_command=True)
    async def config(self, ctx: commands.Context):
        """how you configure your guild"""
        await ctx.send((await self.bot.formatter.format_help_for(ctx, ctx.command))[0])

    @config.command()
    async def get(self, ctx, key):
        """gets the value of a key"""
        cfg = await get_guild_config(self.bot.pool, ctx.guild.id)
        await ctx.send(cfg[str(key)])
        pass
    @config.command()
    async def set(self, ctx, key, value):
        """sets the value of a key"""
        pass

    @config.command()
    async def list(self,ctx):
        """lists the available config keys"""
        cfg = await get_guild_config(self.bot.pool, ctx.guild.id)
        ret = f'your guild config:  ```json\n{cfg}```'
        await ctx.send(ret)


def setup(bot):
    bot.add_cog(Configs(bot))
