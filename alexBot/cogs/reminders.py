import asyncio
import datetime
import logging
import random
import uuid
from functools import lru_cache
from typing import Coroutine, Dict, List, Optional

import discord
import pytz
from discord import app_commands
from discord.ext.commands import Paginator
from sqlalchemy import and_, or_, select

from alexBot import database as db
from alexBot.database import Reminder
from alexBot.tools import Cog, InteractionPaginator, resolve_duration, time_cache

log = logging.getLogger(__name__)


class ClearReminderView(discord.ui.View):
    def __init__(
        self,
    ):
        super().__init__(timeout=None)
        self.waiting = True
        self.times = 0

    @discord.ui.button(label="Clear", style=discord.ButtonStyle.red)
    async def clear(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.waiting = False
        await interaction.response.send_message("Reminder cleared", ephemeral=True)
        self.stop()


class Reminders(Cog):
    tasks: Dict[uuid.UUID, asyncio.Task] = {}
    remind_loop: asyncio.Task = None

    async def cog_load(self):
        # get overdue and soon reminders
        self.remind_loop = self.bot.loop.create_task(self.reminder_loop())

    async def cog_unload(self) -> None:
        self.remind_loop.cancel()
        for item in self.tasks.values():
            item.cancel()

    async def reminder_loop(self):
        while True:
            async with db.async_session() as session:
                time_soon = datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
                stmt = select(Reminder).where(
                    and_(Reminder.next_remind <= time_soon, Reminder.id.not_in(self.tasks.keys()))
                )
                reminders = await session.scalars(stmt)
                for reminder in reminders:
                    if reminder.id not in self.tasks:
                        self.tasks[reminder.id] = self.bot.loop.create_task(self.remind(reminder))
            await asyncio.sleep(60)

    async def remind(self, reminder: Reminder):
        # wait for the reminder time
        now = datetime.datetime.utcnow()
        if now > reminder.next_remind:
            log.warning(f"reminder {reminder} is overdue")
        else:
            await asyncio.sleep((reminder.next_remind - now).total_seconds())
        log.debug(f"reminding {reminder}")
        target = await self.bot.fetch_channel(reminder.target)
        if not target:
            log.error(f"Could not find target {reminder.target} for reminder {reminder}")
            # try to message the owner about it:
            owner = self.bot.get_user(reminder.owner)
            if not owner:
                log.error(f"Could not find owner {reminder.owner} for reminder {reminder}")
                return
            await owner.send(f"Could not find target channel {reminder.target} for reminder {reminder.message}")
            return
        message = reminder.message
        if message.startswith("["):
            # random messages;
            message = reminder.message.lstrip('[')
            messages = message.split(';')
            message = random.choice(messages)

        if reminder.require_clearing:
            v = ClearReminderView()
            dis_message = await target.send(message, view=v)

            while v.waiting and v.times < 8:  # 8 * 5 minutes = 40 minutes
                msg = None
                try:
                    msg = await self.bot.wait_for(
                        "message",
                        check=lambda m: m.channel.id == target.id and m.content.lower().startswith('ack'),
                        timeout=300,
                    )
                    v.waiting = False
                    await msg.reply("reminder cleared")
                except asyncio.TimeoutError:
                    pass
                if v.waiting:
                    v.times += 1
                    await dis_message.reply("reminder!")
        else:
            await target.send(message)

        if reminder.frequency:
            # reschedule the reminder for later
            async with db.async_session() as session:
                async with session.begin():
                    edited = await session.scalar(select(Reminder).where(Reminder.id == reminder.id))
                    if not edited:
                        log.error(f"reminder {reminder} not found in database")
                        return
                    edited.next_remind = (
                        edited.next_remind + reminder.frequency
                    )  # prevent drift by adding the frequency
        else:
            # delete the reminder
            async with db.async_session() as session:
                async with session.begin():
                    delete = await session.scalar(select(Reminder).where(Reminder.id == reminder.id))
                    await session.delete(delete)
        # remove task from tasks dict
        del self.tasks[reminder.id]

    remindersGroup = app_commands.Group(
        name="reminders",
        description="menu for working with reminders",
    )

    @remindersGroup.command(name="add", description="add a new reminder")
    @app_commands.describe(
        message="the message for the reminder. if the message starts with a [, it will be treated as a list of messages to choose from, using ; to seperate them",
        time="when to schedule the reminder, from now in the format xhym",
        require_clearing="if the reminder requires clearing to stop. you can not use this in a guild unless you have the manage guild permission",
        frequency="how often to repeat the reminder, in the format xhym. you can not use this in a guild unless you have the manage guild permission",
    )
    async def add_reminder(
        self,
        interaction: discord.Interaction,
        message: str,
        time: str,
        require_clearing: bool = False,
        frequency: Optional[str] = None,
    ):
        # check limits / validate input
        if interaction.guild and not interaction.user.guild_permissions.manage_guild:
            # we care if they tried to set a recurring in a guild context, or if they tried to set a require_clearing in the guild context
            if require_clearing:
                return await interaction.response.send_message(
                    "You do not have permission to set require_clearing in a guild context.\nYou need manage server permission to do that.",
                    ephemeral=True,
                )
            if frequency:
                return await interaction.response.send_message(
                    "You do not have permission to set frequency in a guild context.\nYou need manage server permission to do that.",
                    ephemeral=True,
                )
        if len(message) > 500:
            return await interaction.response.send_message("Message is too long (Max 500)", ephemeral=True)
        # try to parse the time
        next_remind = None
        try:
            td = resolve_duration(time)
            assert td.total_seconds() >= 120
            next_remind = datetime.datetime.now() + td
        except KeyError:
            return await interaction.response.send_message("Invalid time format", ephemeral=True)
        except AssertionError:
            return await interaction.response.send_message("Time must be in at least 2 minutes", ephemeral=True)
        # check the freqrency is valid (atleast an hour)
        freq = None
        if frequency:
            try:
                freq = resolve_duration(frequency)
                assert freq.total_seconds() >= 3600
            except KeyError:
                return await interaction.response.send_message("Invalid frequency format", ephemeral=True)
            except AssertionError:
                return await interaction.response.send_message("Frequency must be at least 1 hour", ephemeral=True)

        # start a session and create the reminder
        async with db.async_session() as session:
            async with session.begin():
                reminder = Reminder(
                    target=interaction.channel.id,
                    owner=interaction.user.id,
                    guildId=interaction.guild.id if interaction.guild else None,
                    message=message,
                    next_remind=next_remind.replace(microsecond=0),
                    frequency=freq,
                    require_clearing=require_clearing,
                )
                session.add(reminder)
                await session.commit()

        await interaction.response.send_message(
            f"Reminder created with id `{reminder.id}`, at time {discord.utils.format_dt(reminder.next_remind)}",
            ephemeral=False,
        )

    @add_reminder.autocomplete('frequency')
    async def autocomplete_freq(self, interaction: discord.Interaction, frequency: str):
        if interaction.guild and not interaction.user.guild_permissions.manage_guild:
            return [
                discord.app_commands.Choice(
                    name="You do not have permission to use this", value="You do not have permission to use this"
                )
            ]
        else:
            return [
                discord.app_commands.Choice(name="1h", value="1h"),
                discord.app_commands.Choice(name="1d", value="1d"),
                discord.app_commands.Choice(name="1w", value="1w"),
            ]

    @add_reminder.autocomplete('time')
    async def autocomplete_time(self, interaction: discord.Interaction, time: str):
        if not time:
            return [
                discord.app_commands.Choice(name="20m", value="20m"),
                discord.app_commands.Choice(name="1h", value="1h"),
                discord.app_commands.Choice(name="1d", value="1d"),
                discord.app_commands.Choice(name="1w", value="1w"),
                discord.app_commands.Choice(name="1M", value="1M"),
            ]
        else:
            # validate the time field and return the time, if we have the user's timezone, otherwise UTC time
            try:
                td = resolve_duration(time)
                dt = datetime.datetime.now() + td
            except KeyError:
                return [discord.app_commands.Choice(name="Invalid time format", value="Invalid time format")]
            return [
                discord.app_commands.Choice(
                    name=f"reminder at {dt.replace(tzinfo=None).replace(microsecond=0)}", value=time
                )
            ]

    @remindersGroup.command(name="remove", description="remove a reminder")
    async def remove_reminder(self, interaction: discord.Interaction, id: str):
        async with db.async_session() as session:
            reminder = await session.scalar(select(Reminder).where(Reminder.id == uuid.UUID(id)))
            if not reminder:
                return await interaction.response.send_message("Reminder not found", ephemeral=True)
            if reminder.owner != interaction.user.id and not interaction.user.guild_permissions.manage_guild:
                return await interaction.response.send_message(
                    "You do not have permission to manage this reminder", ephemeral=True
                )
            await session.delete(reminder)
            await session.commit()
        await interaction.response.send_message(f"Reminder with messasge `{reminder.message}` deleted", ephemeral=True)

    @time_cache(60)
    def user_can_manage_reminder(self, reminder: Reminder, user: discord.Member):
        if reminder.owner == user.id:
            return True
        if user.guild and user.guild.id == reminder.guildId:
            return user.guild_permissions.manage_guild
        return False

    @remove_reminder.autocomplete('id')
    async def autocomplete_remove(self, interaction: discord.Interaction, msg: str):
        async with db.async_session() as session:
            if interaction.guild and interaction.user.guild_permissions.manage_guild:
                stmt = select(Reminder).where(
                    or_(Reminder.guildId == interaction.guild.id, Reminder.owner == interaction.user.id)
                )
            else:
                stmt = select(Reminder).where(Reminder.owner == interaction.user.id)

            reminders = await session.scalars(stmt)
        reminders = [reminder for reminder in reminders if msg.lower() in reminder.message.lower()]
        return [
            discord.app_commands.Choice(
                name=f"{reminder.message[:25]}{'...' if len(reminder.message)>26 else ''}, at {reminder.next_remind}",
                value=str(reminder.id),
            )
            for reminder in reminders
            if msg.lower() in reminder.message.lower()
        ]

    @remindersGroup.command(name="list", description="list reminders")
    async def list_reminders(self, interaction: discord.Interaction):
        async with db.async_session() as session:
            # are we in a guild, or dms? if we're in a guild, only show that guild's reminders. if we're in dms, show all reminders
            if interaction.guild:
                stmt = select(Reminder).where(Reminder.guildId == interaction.guild.id)
                fmt = "{reminder.next_remind} every {reminder.frequency} by {owner}: `{reminder.message}`"
            else:
                # we must be in dms, get reminders with no guild and the owner is the user
                stmt = select(Reminder).where(and_(Reminder.guildId == None, Reminder.owner == interaction.user.id))
                fmt = "{reminder.next_remind} every {reminder.frequency}: `{reminder.message}`"

            reminders = (await session.scalars(stmt)).all()
            if len(reminders) == 0:
                return await interaction.response.send_message("No reminders found", ephemeral=True)

            paginator = Paginator(prefix="```", suffix="```", max_size=500)
            for reminder in reminders:
                paginator.add_line(fmt.format(reminder=reminder, owner=self.bot.get_user(reminder.owner)))
            pi = InteractionPaginator(self.bot, paginator, owner=None)
            await pi.send_interaction(interaction)
        if not reminders:
            return await interaction.response.send_message("No reminders found", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Reminders(bot))
