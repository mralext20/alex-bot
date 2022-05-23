import asyncio
import logging
import random
import traceback

import discord
from discord.ext import commands

from ..tools import Cog

log = logging.getLogger(__name__)


class CommandErrorHandler(Cog):
    @Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """The event triggered when an error is raised while invoking a command."""
        if isinstance(error, commands.CommandNotFound):
            return

        msg = None
        alex = ctx.bot.owner
        if isinstance(error, asyncio.TimeoutError):
            msg = f"timed out. you can start again with {ctx.prefix}{ctx.command}"

        if isinstance(error, commands.MaxConcurrencyReached):
            if ctx.author.id == 335928292542513162 and random.random() < 0.2:
                msg = "DAWN PLS"
            else:
                msg = f"{ctx.command} is currently being ran. please wait for it to finish."

        if isinstance(error, commands.CommandOnCooldown):
            if ctx.author.id == 335928292542513162 and random.random() < 0.2:
                msg = "DAWN PLS"
            else:
                msg = f"{ctx.command} is being used too often, try again later"

        if isinstance(error, commands.DisabledCommand):
            msg = f'{ctx.command} has been disabled.'

        elif isinstance(error, commands.NotOwner):
            msg = f'{ctx.command} is a owner only command.'

        elif isinstance(error, commands.NoPrivateMessage):
            msg = f'{ctx.command} can not be used in Private Messages.'

        elif isinstance(error, commands.BadArgument):
            ctx.command.reset_cooldown(ctx)
            msg = f'Bad argument: {error} See {ctx.prefix}help {ctx.command} for help!'
            log.warning(f"bad argument on {ctx.command}: {error}")

        elif isinstance(error, commands.CheckFailure):
            msg = 'A Check failed for this command.'

        elif isinstance(error, commands.MissingRequiredArgument):
            msg = f'Parameter {error.param} is required but missing, See {ctx.prefix}help {ctx.command} for help!'
        elif isinstance(error, commands.MissingPermissions):
            msg = 'You do not have permission to run that command.'
        elif isinstance(error, commands.CommandInvokeError):
            error = error.original

            if isinstance(error, discord.Forbidden):
                msg = (
                    'A permission error occurred while executing this command, '
                    'Make sure I have the required permissions and try again.'
                )

        # post the error into the chat if no short error message could be generated
        if not msg:
            trace = traceback.format_exception(type(error), error, error.__traceback__, limit=5)
            actual_trace = '\n'.join(trace)
            msg = (
                f"Something, somewhere, broke. if {alex.mention} isnt in this server, "
                f"so you'll have to join the server in `a!about`."
            )
            log.error(
                f"{ctx.author.id} broke bot running {ctx.command.cog_name}.{ctx.command.qualified_name}"
                f"\nquotable: {ctx.channel.id or 'DM'}-{ctx.message.id or None}\n"
                f":{actual_trace}"
            )

        allowed_mentions = discord.AllowedMentions(users=[ctx.bot.owner])

        try:
            await ctx.send(msg, allowed_mentions=allowed_mentions)
        except discord.HTTPException:
            await ctx.send('error message too long')


async def setup(bot: commands.Bot):
    await bot.add_cog(CommandErrorHandler(bot))
