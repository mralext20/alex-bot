import asyncio
import datetime
import logging
from typing import List, Optional
import discord
from alexBot.classes import RecurringReminder
from discord import app_commands
from alexBot.tools import Cog

log = logging.getLogger(__name__)


class ClearReminderView(discord.ui.View):
    def __init__(
        self,
    ):
        super().__init__(timeout=300)
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
            self.tasks.append(self.bot.loop.create_task(self.remind(reminder)))

    async def cog_unload(self) -> None:
        for task in self.tasks:
            task.cancel()

    async def setup_remind(self, reminder: RecurringReminder):
        now = datetime.datetime.utcnow()
        curr_minute = now.minute + now.hour * 60
        reminder_minute = reminder.UTC_minute
        if curr_minute > reminder_minute:
            reminder_minute += 1440
        delta = datetime.timedelta(minutes=reminder_minute - curr_minute)
        await discord.utils.sleep_until(now + delta)
        await self.remind(reminder)

    async def remind(self, reminder: RecurringReminder):
        target = self.bot.get_channel(reminder.target) or self.bot.get_user(reminder.target)
        if not target:
            log.warning(f"Could not find target {reminder.target} for reminder {reminder}")
            return
        self.tasks.append(self.bot.loop.create_task(self.remind(reminder)))
        if reminder.require_clearing:
            v = ClearReminderView()
            message = await target.send(reminder.message, view=v)

            while v.waiting:
                await asyncio.sleep(300)
                if v.waiting:
                    await message.reply("reminder!")

            return
        await target.send(reminder.message)

    remindersGroup = app_commands.Group(
        name="reminders", description="menu for working with reminders", guild_ids=[791528974442299412]
    )

    @remindersGroup.command(name="add", description="add a new reminder")
    @app_commands.describe(time="the time in mminutes after UTC Midnight to run the reminder at")
    @app_commands.describe(require_clearing="if the reminder requires clearing to stop")
    @app_commands.describe(target="if set, will send the reminder to this set channel instead of the user")
    async def add_reminder(
        self,
        interaction: discord.Interaction,
        message: str,
        time: int,
        target: Optional[discord.TextChannel],
        require_clearing: bool = False,
    ):
        if target:
            if not target.permissions_for(interaction.user).manage_channels:
                await interaction.response.send_message(
                    "You do not have permission to set reminders in that channel",
                    ephemeral=True,
                )
                return

        reminder = RecurringReminder(
            target=target.id if target else interaction.user.id,
            message=message,
            UTC_minute=time,
            require_clearing=require_clearing,
        )
        self.reminders.append(reminder)
        await self.bot.db.save_recurring_reminders(self.reminders)

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
                return
        await interaction.response.send_message("Reminder not found")


async def setup(bot):
    await bot.add_cog(RecurringReminders(bot))
