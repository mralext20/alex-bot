import asyncio
import logging
import random
import traceback

import discord
from discord import Interaction
from discord.app_commands import AppCommandError
from discord.ext import commands

from ..tools import Cog

log = logging.getLogger(__name__)


class CommandErrorHandler(Cog):
    def cog_load(self):
        tree = self.bot.tree
        self._old_tree_error = tree.on_error
        tree.on_error = self.on_app_command_error

    def cog_unload(self):
        tree = self.bot.tree
        tree.on_error = self._old_tree_error

    # -> Option 1 ---
    # the global error handler for all app commands (slash & ctx menus)
    async def on_app_command_error(self, interaction: Interaction, error: AppCommandError):
        log.error(f"app command error: {error} from {interaction.user} in {interaction.guild or 'DM'}")
        log.exception(error)
        if interaction.response.is_done():
            await interaction.followup.send(
                f"An Error Occurred while running this command. please contact {self.bot.owner.mention}", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"An Error Occurred while running this command. please contact {self.bot.owner.mention}", ephemeral=True
            )

    @Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception):

        error_messages = {
            commands.DisabledCommand: lambda: (f'{ctx.command} has been disabled.', None),
            commands.NotOwner: lambda: (f'{ctx.command} is a owner only command.', None),
            commands.NoPrivateMessage: lambda: (f'{ctx.command} can not be used in Private Messages.', None),
            commands.CheckFailure: lambda: ('A Check failed for this command.', None),
            commands.MissingRequiredArgument: lambda: (
                f'Parameter {error.param} is required but missing, See {ctx.prefix}help {ctx.command} for help!',
                None,
            ),
            commands.MissingPermissions: lambda: ('You do not have permission to run that command.', None),
            commands.CommandOnCooldown: lambda: (f"{ctx.command} is being used too often, try again later", None),
            commands.MaxConcurrencyReached: lambda: (
                f"{ctx.command} is currently being ran. please wait for it to finish.",
                None,
            ),
            asyncio.TimeoutError: lambda: (f"timed out. you can start again with {ctx.prefix}{ctx.command}", None),
            commands.BadArgument: lambda: (
                f'Bad argument: {error} See {ctx.prefix}help {ctx.command} for help!',
                ctx.command.reset_cooldown(ctx),
            ),
        }

        """The event triggered when an error is raised while invoking a command."""
        if isinstance(error, commands.CommandNotFound):
            return

        msg = None
        if isinstance(error, asyncio.TimeoutError):
            msg = f"timed out. you can start again with {ctx.prefix}{ctx.command}"

        if any(isinstance(error, e) for e in error_messages):
            msg = error_messages[type(error)]()[0]  # type: ignore  # no fail because we just checked for existing keys

        if isinstance(error, commands.CommandInvokeError) and isinstance(error.original, discord.Forbidden):
            error = error.original

            msg = 'A permission error occurred while executing this command, Make sure I have the required permissions and try again.'

        # post the error into the chat if no short error message could be generated
        if not msg:
            trace = traceback.format_exception(type(error), error, error.__traceback__, limit=5)
            actual_trace = '\n'.join(trace)
            msg = (
                f"Something, somewhere, broke. if {ctx.bot.owner.mention} isnt in this server, "
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
