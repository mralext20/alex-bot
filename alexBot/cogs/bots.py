# -*- coding: utf-8 -*-

import datetime
import logging

import discord

from ..tools import Cog

import asyncio

log = logging.getLogger(__name__)


class Bots(Cog):
    """Bot downtime notifications."""
    pending_messages = {}

    @Cog.listener()
    async def on_member_update(self, before, after):
        if before.id not in self.bot.config.monitored_bots or before.status == after.status:
            return

        # we only notify when a bot goes offline or comes back online
        if not any(x.status is discord.Status.offline for x in (before, after)):
            return

        config = self.bot.config.monitored_bots[before.id]
        # we only care about in the notification guild
        if config['shared_guild'] != before.guild.id:
            return

        messagable = self.bot.get_user(config['messagable_id'])
        if messagable is None:
            messagable = self.bot.get_channel(config['messagable_id'])

        status = after.status

        if status is discord.Status.offline:
            msg = f'\N{WARNING SIGN} `{before} {before.id}` just went offline'
            wait = 30
        else:
            msg = f'\N{PARTY POPPER} `{before} {before.id}` just came back online'
            wait = 0
            if (before.id in self.pending_messages.keys()):
                if self.pending_messages[before.id].done():
                    del self.pending_messages[before.id]
                else:
                    self.pending_messages[before.id].cancel()
                    del self.pending_messages[before.id]
                    return

        log.debug(f'Sending notification about {before} ({before.id}) going {status}.')

        now = datetime.datetime.utcnow().strftime('`[%H:%M]`')

        try:
            self.pending_messages[before.id] = asyncio.get_event_loop().create_task(
                self.send(messagable, f'{now} {msg}', wait)
            )
        except discord.HTTPException:
            pass

    @staticmethod
    async def send(messagable, message, wait=30):
        """sends a message to a messagable after 30 seconds unless cancled"""
        await asyncio.sleep(wait)
        await messagable.send(message)


def setup(bot):
    bot.add_cog(Bots(bot))
