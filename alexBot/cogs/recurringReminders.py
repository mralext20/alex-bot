import asyncio
import datetime
import logging
import random
from typing import Coroutine, List, Optional

import discord
from discord import app_commands

from alexBot.classes import RecurringReminder
from alexBot.tools import Cog, resolve_duration

log = logging.getLogger(__name__)


class ClearReminderView(discord.ui.View):
    def __init__(
        self,
    ):
        super().__init__(timeout=None)
        self.waiting = True

    @discord.ui.button(label="Clear", style=discord.ButtonStyle.red)
    async def clear(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.waiting = False
        await interaction.response.send_message("Reminder cleared", ephemeral=True)
        self.stop()


class RecurringReminders(Cog):
    def __init__(self, bot: "Bot"):
        super().__init__(bot)
        self.tasks = []
        self.reminders: List[RecurringReminder] = []

    async def cog_load(self):
        self.reminders = await self.bot.db.get_recurring_reminders()
        for reminder in self.reminders:
            self.tasks.append(self.bot.loop.create_task(self.setup_remind(reminder)))

    async def cog_unload(self) -> None:
        for task in self.tasks:
            task.cancel()

    @staticmethod
    async def wait_a_moment(partial: Coroutine):
        await asyncio.sleep(125)
        await partial

    async def setup_remind(self, reminder: RecurringReminder):
        await self.bot.wait_until_ready()
        now = datetime.datetime.utcnow()
        curr_minute = now.minute + now.hour * 60
        reminder_minute = reminder.UTC_minute
        if curr_minute > reminder_minute:
            reminder_minute += 1440
        delta = datetime.timedelta(minutes=reminder_minute - curr_minute)
        await discord.utils.sleep_until(now + delta)
        await self.remind(reminder)

    async def remind(self, reminder: RecurringReminder):
        log.debug(f"reminding {reminder}")
        target = self.bot.get_channel(reminder.target) or self.bot.get_user(reminder.target)
        if not target:
            log.warning(f"Could not find target {reminder.target} for reminder {reminder}")
            return
        self.bot.loop.create_task(self.wait_a_moment(self.setup_remind(reminder)))
        message = reminder.message
        if message.startswith("["):
            # random messages;
            message = reminder.message.lstrip('[')
            messages = message.split(',')
            message = random.choice(messages)

        if reminder.require_clearing:
            v = ClearReminderView()
            dis_message = await target.send(message, view=v)

            while v.waiting:
                await asyncio.sleep(300)
                if v.waiting:
                    await dis_message.reply("reminder!")

            return
        else:
            await target.send(message)

    remindersGroup = app_commands.Group(
        name="recurring-reminders",
        description="menu for working with reminders",
    )

    @remindersGroup.command(name="add", description="add a new reminder")
    @app_commands.describe(time="when to schedule the reminder, from now in the format xhym")
    @app_commands.describe(require_clearing="if the reminder requires clearing to stop")
    @app_commands.describe(target="if set, will send the reminder to this set channel instead of the user")
    async def add_reminder(
        self,
        interaction: discord.Interaction,
        message: str,
        time: str,
        target: Optional[discord.TextChannel],
        require_clearing: bool = False,
    ):
        try:
            dt = resolve_duration(time)
            if dt.hour > 23 or dt.minute > 59:
                await interaction.response.send_message("time too long :(", ephemeral=True)
                return
        except KeyError:
            await interaction.response.send_message("Invalid time format", ephemeral=True)
            return
        if target:
            if not target.permissions_for(interaction.user).manage_channels:
                await interaction.response.send_message(
                    "You do not have permission to set reminders in that channel",
                    ephemeral=True,
                )
                return
        time_min = dt.minute + dt.hour * 60
        reminder = RecurringReminder(
            target=target.id if target else interaction.user.id,
            message=message,
            UTC_minute=time_min,
            require_clearing=require_clearing,
        )
        self.reminders.append(reminder)
        await self.bot.db.save_recurring_reminders(self.reminders)
        self.tasks.append(self.bot.loop.create_task(self.setup_remind(reminder)))
        await interaction.response.send_message("Reminder added")

    @remindersGroup.command(name="remove", description="remove a reminder")
    async def remove_reminder(self, interaction: discord.Interaction, message: str):
        for reminder in self.reminders:
            if reminder.message == message:
                if reminder.target != interaction.user.id:
                    await interaction.response.send_message(
                        "You do not have permission to remove that reminder",
                        ephemeral=True,
                    )
                    return
                target = self.bot.get_channel(reminder.target)
                if target and not target.permissions_for(interaction.user).manage_channels:
                    await interaction.response.send_message(
                        "You do not have permission to set reminders in that channel",
                        ephemeral=True,
                    )
                    return
                self.reminders.remove(reminder)
                await self.bot.db.save_recurring_reminders(self.reminders)
                await interaction.response.send_message("Reminder removed")
                await self.bot.reload_extension("alexBot.cogs.recurringReminders")
                return
        await interaction.response.send_message("Reminder not found")

    def user_can_manage_reminder(self, reminder: RecurringReminder, user: discord.Member):
        if reminder.target == user.id:
            return True
        target_chan = self.bot.get_channel(reminder.target)
        if not target_chan:
            return False
        if target_chan.permissions_for(user).manage_channels:
            return True
        return False

    @remove_reminder.autocomplete('message')
    async def autocomplete_remove(self, interaction: discord.Interaction, msg: str):
        reminders = [
            reminder for reminder in self.reminders if self.user_can_manage_reminder(reminder, interaction.user)
        ]
        return [
            discord.app_commands.Choice(name=reminder.message, value=reminder.message)
            for reminder in reminders
            if msg.lower() in reminder.message.lower()
        ]


async def setup(bot):
    await bot.add_cog(RecurringReminders(bot))
