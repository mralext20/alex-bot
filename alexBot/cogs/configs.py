from discord.ext import commands
import discord

from ..tools import Cog
from ..tools import get_guild_config
from ..tools import BoolConverter
from ..tools import update_guild_key


class Configs(Cog):
    """handles guild config settings"""
    @commands.group(name="config", invoke_without_command=True)
    async def config(self, ctx: commands.Context):
        """how you configure your guild"""
        await ctx.send((await self.bot.formatter.format_help_for(ctx, ctx.command))[0])

    @config.command()
    async def get(self, ctx, key):
        """gets the value of a key"""
        cfg = await get_guild_config(self.bot, ctx.guild.id)
        try:
            cfg[key]
        except KeyError:
            raise commands.BadArgument(f'the key {key} does not exist')
        await ctx.send(cfg[str(key)])
        pass

    @config.command()
    async def set(self, ctx: commands.Context, key, value):
        """sets the value of a key"""
        cfg = await get_guild_config(self.bot, ctx.guild.id)
        try:
            old = cfg[key]
        except KeyError:
            raise commands.BadArgument(f'the key {key} does not exist!')
        if type(old) == bool:
            value = await BoolConverter.convert(self, ctx, value)

        await update_guild_key(self.bot, ctx.guild.id, key, value)
        try:
            await ctx.message.add_reaction('\U00002705')
        except discord.HTTPException:
            await ctx.send('\U00002705')

    @config.command()
    @commands.has_permissions(manage_guild=True)
    async def list(self, ctx):
        """lists the available config keys"""
        cfg = await get_guild_config(self.bot, ctx.guild.id)
        ret = f'your guild config:  ```json\n{cfg}```'
        await ctx.send(ret)


def setup(bot):
    bot.add_cog(Configs(bot))
