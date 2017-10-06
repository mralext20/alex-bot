"""
"""


import discord
from discord.ext import commands
import inspect

from ..tools import Cog


class Exec(Cog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._last_result = None

    @commands.command(hidden=True)
    @commands.is_owner()
    async def eval(self, ctx, *, command: str):
        """
        eval's a command
        """
        env = {
            'self': self,
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            '_': self._last_result
        }
        env.update(globals())

        has_been_awaited = False
        try:
            result = eval(command, env)
            if inspect.isawaitable(result):
                result = await result
                has_been_awaited = True
        except Exception as err:
            result = repr(err)
        self._last_result = result
        result_too_big = len(str(result)) > 2000
        if ctx.channel.permissions_for(ctx.me).embed_links:
            color = discord.Color(0)
            if isinstance(result, discord.Colour):
                color = result
            emb = discord.Embed(description=f"{result}"[:2000],
                                color=color)
            emb.set_footer(text=f"{result.__class__.__module__}.\
            {result.__class__.__name__} \
            {'| Command has been awaited' if has_been_awaited else ''} \
            {'| Result has been cut' if result_too_big else ''}")
            await ctx.send(embed=emb)
        else:
            await ctx.send(
                f"```xl\nOutput: {str(result)[:1500]}\n\
                Output class: {result.__class__.__module__}.\
                {result.__class__.__name__}```")

    @commands.command(name='sh')
    @commands.is_owner()
    async def shell(self, ctx, *, cmd):
        """Run a subprocess using shell."""
        async with ctx.typing():
            result = await run_subprocess(cmd)
        await ctx.send(f'```{result}```')

    @commands.command()
    @commands.is_owner()
    async def reloadutils(self,ctx):
        """Reload the utils cog"""
        try:
            self.bot.unload_extension("alexBot.cogs.utils")
            self.bot.load_extension("alexBot.cogs.utils")
        except Exception as e:
            await ctx.send(f'**`ERROR:`** {type(e).__name__} - {e}')
        else:
            await ctx.send('**`SUCCESS`**')


    @commands.command()
    @commands.is_owner()
    async def download(self, ctx, file):
        """Attaches a stored file"""
        with open(file, 'rb') as f:
            try:
                await ctx.send(file = discord.File(f, file))
            except FileNotFoundError:
                await ctx.send(f"no such file: {file}")

    @commands.command()
    @commands.is_owner()
    async def upload(self, ctx):
        """Upload a file"""
        attachments = ctx.message.attachments
        # TODO: allow this to wait_for a upload file from the original sender.
        if attachments is None:
            ctx.send("please upload a file in the same message.")
            return

        for attachment in attachments:
            with open(attachment.filename, "wb") as f:
                attachment.save(f)
            await ctx.send(f"saved as {attachment.filename}")



def setup(bot):
    bot.add_cog(Exec(bot))
