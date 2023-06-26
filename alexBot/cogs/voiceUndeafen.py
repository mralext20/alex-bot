import asyncio
import ctypes
from datetime import datetime, timedelta
import logging
import os
from io import BytesIO
from typing import Dict, List, Optional, Tuple

import discord
from asyncgTTS import (
    AsyncGTTSSession,
    ServiceAccount,
    SynthesisInput,
    TextSynthesizeRequestBody,
)
from discord import app_commands
from alexBot.classes import UndefenTimes

from alexBot.tools import Cog, resolve_duration

log = logging.getLogger(__name__)

DAYS_OF_THE_WEEK = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


class VoiceUndeafenTimers(Cog):
    def __init__(self, bot: "Bot"):
        self.timers: List[asyncio.Task] = []

    async def cog_load(self):
        self.bot.voiceCommandsGroup.add_command(
            app_commands.Command(
                name="add-undeafen-times",
                description="automaticly undeafen yourself at a sepcific time by day of the week.",
                callback=self.add_deafen_times,
            )
        )
        self.bot.voiceCommandsGroup.add_command(
            app_commands.Command(
                name="remove-undeafen-times",
                description="remove automatic undeafens.",
                callback=self.add_deafen_times,
            )
        )

    async def cog_unload(self) -> None:
        for timer in self.timers:
            timer.cancel()
        self.bot.voiceCommandsGroup.remove_command("add-undeafen-times")

    @app_commands.describe(times="the times you want to undeafen yourself at, send remove to remove all times")
    async def add_deafen_times(self, interaction: discord.Interaction, times: str):
        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in a guild", ephemeral=True)
            return
        if len(times.split()) != 7:
            await interaction.response.send_message(
                "You need to send 7 times, one for each day of the week, Sunday, Monday, Tuesday, Wednesday, Thursday, Friday, Saturday",
                ephemeral=True,
            )
            return

        new_times: List[Optional[int]] = []

        for time in times.split():
            # format should be compatible with tools.resolve_duration
            if time == 'none':
                new_times.append(None)
                continue
            try:
                nt = resolve_duration(time)
                if nt.hour > 23 or nt.minute > 59:
                    await interaction.response.send_message("time too long :(", ephemeral=True)
                    return
            except KeyError:
                await interaction.response.send_message(
                    f"Invalid time format: {time}. should look like 1h20m", ephemeral=True
                )
                return
            # convert the datetime from when it needs to happen to a utc minute
            nt = nt.minute + nt.hour * 60
            new_times.append(nt)

        # confirm the times with the user:
        v = ViewConfirmer()
        dts: List[Optional[datetime]] = []
        now = datetime.utcnow()
        for t in new_times:
            if t is None:
                dts.append(None)
                continue
            now = datetime.utcnow()
            curr_minute = now.minute + now.hour * 60
            if curr_minute > t:
                t += 1440
            delta = timedelta(minutes=t - curr_minute)

            dts.append(now + delta)
        self.stamps = dts
        times_str = ""
        for weekday, dt in zip(DAYS_OF_THE_WEEK, dts):
            # discord can auto-convert the timezone for us if we put it in <t:UNIX_STAMP:t>
            if dt is None:
                times_str += f"{weekday}: No Action\n"
                continue
            times_str += f"{weekday}: <t:{int(dt.timestamp())}:R>\n"

        # TODO: this is going to be a problem because timezones are stupid. how do we know that the user's sunday is the same as the bot's sunday? we don't.
        # i'm going to commit this code to a new branch and hope i cope up with a better solution later.

        await interaction.response.send_message(
            "are you sure you want to auto undefen at these times?\n" + times_str, view=v
        )

        await v.wait()
        if v.timed_out:
            await interaction.response.send_message("Timed out.", ephemeral=True)
            return
        if not v.success:
            await interaction.response.send_message("Cancelled.", ephemeral=True)
            return

        udt = UndefenTimes(times=new_times, userId=interaction.user.id, guildId=interaction.guild.id)

        await self.bot.db.add_undeafenTimer(udt)
        await interaction.followup.send("Added times", ephemeral=True)


class ViewConfirmer(discord.ui.View):
    def __init__(self, *, timeout: float | None = 300):
        super().__init__(timeout=timeout)
        self.timed_out = True
        self.success: Optional[bool] = None

        @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
        async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.success = True
            self.timed_out = False
            self.stop()

        @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
        async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.success = False
            self.timed_out = False
            self.stop()


async def setup(bot):
    await bot.add_cog(VoiceUndeafenTimers(bot))
