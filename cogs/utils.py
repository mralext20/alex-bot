# -*- coding: utf-8 -*-

from discord.ext import commands


class Utils:
    """The description for Utils goes here."""

    def __init__(self, bot):
        self.bot = bot


    @commands.command(name='reload', hidden=True)
    @commands.is_owner()
    async def cog_reload(self, ctx, *, cog: str):
        """Command which Reloads a Module.
        Remember to use dot path. e.g: cogs.owner"""

        try:
            self.bot.unload_extension(cog)
            self.bot.load_extension(cog)
        except Exception as e:
            await ctx.send(f'**`ERROR:`** {type(e).__name__} - {e}')
        else:
            await ctx.send('**`SUCCESS`**')


    @commands.command()
    async def ping(self, ctx):
        await ctx.send(f"Pong! time is {round(ctx.bot.latency * 1000, 2)} ms")


def setup(bot):
    bot.add_cog(Utils(bot))
