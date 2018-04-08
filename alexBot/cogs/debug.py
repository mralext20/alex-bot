# -*- coding: utf-8 -*-

"""
MIT License
Copyright (c) 2017 - 2018 FrostLuma
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import asyncio
import inspect
import textwrap

import asyncpg
import discord
from discord.ext import commands

from alexBot.tools import Cog, shell, Timer
from alexBot.formatting import clean_codeblock, Table


IMPLICIT_RETURN_BLACKLIST = {
    'assert', 'break', 'continue', 'del', 'from', 'import', 'pass', 'raise', 'return', 'with', 'yield'
}


class Debug(Cog):
    """Commands to debug the Bot and make running it easier."""

    def __init__(self, bot):
        super().__init__(bot)

        # list of actively running eval sessions to allow cancelling them
        self.active = set()

    async def __local_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    def __unload(self):
        self._cancel_sessions()

    @commands.command(aliases=['logout'])
    async def stop(self, ctx):
        """Stop alex Bot."""
        await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")
        await self.bot.logout()

    @commands.command()
    async def update(self, ctx):
        """Update from git."""
        async with ctx.typing():
            result = await shell('git pull')
            await ctx.send(f'```{result}```')

    @commands.command(aliases=['sh'])
    async def shell(self, ctx, *, command: clean_codeblock):
        """Run shell commands."""
        async with ctx.typing():
            output = await shell(command)
            await ctx.send(f'```sh\n{output}```')

    @commands.command()
    async def sql(self, ctx, *, statement: clean_codeblock):
        """Execute SQL queries."""
        async with ctx.typing():
            # this is probably not the ideal solution but it works
            if 'select' in statement.lower():
                coro = self.bot.pool.fetch
            else:
                coro = self.bot.pool.execute

            try:
                with Timer() as timer:
                    result = await coro(statement)
            except asyncpg.PostgresError as e:
                return await ctx.send(f'Failed to execute! {type(e).__name__}: {e}')

            # execute returns the status as a string
            if isinstance(result, str):
                return await ctx.send(f'```py\n{result}```took {timer}')

            if not result:
                return await ctx.send(f'no results, took {timer}')

            # render output of statement
            columns = list(result[0].keys())
            table = Table(*columns)

            for row in result:
                values = [str(x) for x in row]
                table.add_row(*values)

            rendered = await table.render(self.bot.loop)

            # properly emulate the psql console
            rows = len(result)
            rows = f'({rows} row{"s" if rows > 1 else ""})'

            await ctx.send(f'```py\n{rendered}\n{rows}```took {timer}')

    @commands.group(name='eval', aliases=['exec', 'debug'], invoke_without_command=True)
    async def eval_(self, ctx, *, code: clean_codeblock):
        """Execute Python code."""

        env = {
            # common imports
            'asyncio': asyncio,
            'discord': discord,
            'commands': commands,

            # ctx shortcuts
            'author': ctx.author,
            'channel': ctx.channel,
            'ctx': ctx,
            'guild': ctx.guild,
            'message': ctx.message,

            # Bot shortcuts
            'bot': self.bot,
            'pool': self.bot.pool,
            'loop': self.bot.loop,
            'session': self.bot.session,
        }

        def compile_code(insert_return=False):
            _code = f'return {code}' if insert_return else code

            _code = textwrap.indent(_code, '    ')
            func = f'async def cheese():\n{_code}'

            # add the function to the environment, check for syntax errors
            exec(compile(func, '<debug session>', mode='exec'), env)

        compiled = False

        # if the code is a single line and there are no blacklisted keywords we attempt return automatically
        if len(code.split('\n')) < 2 and not any(x in code for x in IMPLICIT_RETURN_BLACKLIST):
            try:
                compile_code(insert_return=True)
            except SyntaxError:
                pass
            else:
                compiled = True

        if not compiled:
            try:
                compile_code(code)
            except SyntaxError as e:
                if e.text is None:
                    return await ctx.send(f'```py\n{e.__class__.__name__}: {e}```')

                arrow = '^'  # this can't be put into the f string as it's a formatting specifier

                error = f"""
                ```py
                File "{e.filename}", line {e.lineno}
                {e.text}\
                {arrow:>{e.offset}}
                {e.__class__.__name__}: {e.msg}```
                """

                return await ctx.send(inspect.cleandoc(error))

        # retrieve function out of env
        cheese = env['cheese']

        async def late_reaction():
            await asyncio.sleep(2.5)
            await ctx.message.add_reaction('\N{HOURGLASS WITH FLOWING SAND}')

        # if the code takes more than 2.5 seconds to run indicate it's actually running by adding a reaction
        react = self.bot.loop.create_task(late_reaction())

        task = self.bot.loop.create_task(cheese())
        self.active.add(task)

        try:
            with Timer() as timer:
                await asyncio.gather(task)
        except asyncio.CancelledError:
            return  # no need to send a message to the channel if the session is cancelled
        except Exception as e:
            return await ctx.send(f'```py\n{repr(e)}```')
        finally:
            self.active.remove(task)

            if not react.done():
                react.cancel()

        result = task.result()

        output = [f'took {timer}']

        if result is not None:
            if not isinstance(result, str):
                result = repr(result)

            output.append(f'ret value\n---------\n{result}')

        formatted = '\n'.join(output)
        await ctx.send(f'```py\n{formatted}```')

    @eval_.command()
    async def cancel(self, ctx):
        """Cancel all active debug sessions."""

        self._cancel_sessions()
        await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")

    def _cancel_sessions(self):
        for task in self.active:
            task.cancel()

    @commands.command()
    @commands.is_owner()
    async def download(self, ctx, file):
        """Attaches a stored file"""
        with open(file, 'rb') as f:
            try:
                await ctx.send(file=discord.File(f, file))
            except FileNotFoundError:
                await ctx.send(f"no such file: {file}")

    @commands.command()
    @commands.is_owner()
    async def upload(self, ctx):
        """Upload a file"""
        attachments = ctx.message.attachments

        if not attachments:
            await ctx.send("No attachment found! Please upload it in your next message.")

            def check(msg_: discord.Message) -> bool:
                return msg_.channel.id == ctx.channel.id and msg_.author.id == ctx.author.id and msg_.attachments

            try:
                msg = await self.bot.wait_for('message', check=check, timeout=60 * 10)
            except asyncio.TimeoutError:
                return await ctx.send('Stopped waiting for file upload, 10 minutes have passed.')

            attachments = msg.attachments

        for attachment in attachments:
            with open(attachment.filename, "wb") as f:
                attachment.save(f)
            await ctx.send(f"saved as {attachment.filename}")

    @commands.command()
    @commands.is_owner()
    async def reload(self, ctx, cog):
        """Reload the admin cog"""
        try:
            self.bot.unload_extension(f"alexBot.cogs.{cog}")
            self.bot.load_extension(f"alexBot.cogs.{cog}")
        except Exception as e:
            await ctx.send(f'**`ERROR:`** {type(e).__name__} - {e}')
        else:
            await ctx.send('**`SUCCESS`**')


def setup(bot):
    bot.add_cog(Debug(bot))
