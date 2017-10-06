"""
Handy exec (eval, debug) cog. Allows you to run code on the bot during runtime. This cog
is a combination of the exec commands of other bot authors:

Credit:
    - Rapptz (Danny)
        - https://github.com/Rapptz/RoboDanny/blob/master/cogs/repl.py#L31-L75
    - b1naryth1ef (B1nzy, Andrei)
        - https://github.com/b1naryth1ef/b1nb0t/blob/master/plugins/util.py#L220-L257

Features:
    - Strips code markup (code blocks, inline code markup)
    - Access to last result with _
    - _get and _find instantly available without having to import discord
    - Redirects stdout so you can print()
    - Sane syntax error reporting
    - Quickly retry evaluations
"""

import asyncio
import io
import logging
import textwrap
import traceback
from contextlib import redirect_stdout

import aiohttp
import discord
from discord.ext import commands
import inspect
import os
import asyncio

from ..tools import Cog
from .haste import haste

log = logging.getLogger(__name__)


def strip_code_markup(content: str) -> str:
    """ Strips code markup from a string. """
    # ```py
    # code
    # ```
    if content.startswith('```') and content.endswith('```'):
        # grab the lines in the middle
        return '\n'.join(content.split('\n')[1:-1])

    # `code`
    return content.strip('` \n')


async def run_subprocess(cmd: str) -> str:
    """Runs a subprocess and returns the output."""
    process = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    results = await process.communicate()
    return "".join(x.decode("utf-8") for x in results)


def format_syntax_error(e: SyntaxError) -> str:
    """ Formats a SyntaxError. """
    if e.text is None:
        return '```py\n{0.__class__.__name__}: {0}\n```'.format(e)
    # display a nice arrow
    return '```py\n{0.text}{1:>{0.offset}}\n{2}: {0}```'.format(e, '^', type(e).__name__)


class Exec(Cog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.last_result = None
        self.previous_code = None

    async def execute(self, ctx, code):
        log.info('Eval: %s', code)

        async def upload(file_name: str):
            with open(file_name, 'rb') as fp:
                await ctx.send(file=discord.File(fp))

        async def send(*args, **kwargs):
            await ctx.send(*args, **kwargs)

        env = {
            'bot': ctx.bot,
            'ctx': ctx,
            'msg': ctx.message,
            'guild': ctx.guild,
            'channel': ctx.channel,
            'me': ctx.message.author,

            # modules
            'discord': discord,
            'commands': commands,

            # utilities
            '_get': discord.utils.get,
            '_find': discord.utils.find,
            '_upload': upload,
            '_send': send,

            # last result
            '_': self.last_result,
            '_p': self.previous_code
        }
        env.update(globals())

        # simulated stdout
        stdout = io.StringIO()

        # wrap the code in a function, so that we can use await
        wrapped_code = 'async def func():\n' + textwrap.indent(code, '    ')

        # define the wrapped function
        try:
            exec(compile(wrapped_code, '<exec>', 'exec'), env)
        except SyntaxError as e:
            return await ctx.send(format_syntax_error(e))

        func = env['func']
        try:
            # execute the code
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            # something went wrong
            try:
                await ctx.message.add_reaction('\N{EXCLAMATION QUESTION MARK}')
            except:
                pass
            stream = stdout.getvalue()
            await ctx.send('```py\n{}{}\n```'.format(stream, traceback.format_exc()))
        else:
            # successful
            stream = stdout.getvalue()

            try:
                await ctx.message.add_reaction('\N{HUNDRED POINTS SYMBOL}')
            except:
                # couldn't add the reaction, ignore
                log.warning('Failed to add reaction to eval message, ignoring.')

            try:
                self.last_result = self.last_result if ret is None else ret
                await ctx.send('```py\n{}{}\n```'.format(stream, repr(ret)))
            except discord.HTTPException:
                # too long
                try:
                    url = await haste(ctx.bot.session, stream + repr(ret))
                    await ctx.send(await ctx._('cmd.eval.long', url))
                except KeyError:
                    # even hastebin couldn't handle it
                    await ctx.send(await ctx._('cmd.eval.huge'))
                except aiohttp.ClientError:
                    await ctx.send(await ctx._('cmd.eval.pastebin_down'))

    @commands.command(name='retry', hidden=True)
    @commands.is_owner()
    async def retry(self, ctx):
        """ Retries the previously executed Python code. """
        if not self.previous_code:
            return await ctx.send('No previous code.')

        await self.execute(ctx, self.previous_code)

    @commands.command(name='eval', aliases=['exec', 'debug'])
    @commands.is_owner()
    async def _eval(self, ctx, *, code: str):
        """ Executes Python code. """

        # remove any markup that might be in the message
        # TODO: converter
        code = strip_code_markup(code)

        # store previous code
        self.previous_code = code

        await self.execute(ctx, code)

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

    @commands.command()
    @commands.is_owner()
    async def restart(self,ctx):
        try:
            assert os.uname().nodename == "raspberrypi"
        except AssertionError:
            await ctx.send("ERROR: cant restart, im not running on a pi")
        pm2_id = os.environ["pm_id"]
        await ctx.send("shutting down....")
        run_subprocess(f"pm2 restart {pm2_id}")
        await ctx.send("sent restart to pm2!")



def setup(bot):
    bot.add_cog(Exec(bot))
