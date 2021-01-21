# -*- coding: utf-8 -*-

import datetime
import logging
from typing import Dict

import discord

from ..tools import Cog

import asyncio

log = logging.getLogger(__name__)


class Bots(Cog):
    """Bot downtime notifications."""

    pending_messages: Dict[object, asyncio.Task] = {}

    @Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.id not in self.bot.config.monitored_bots or before.status == after.status:
            return

        # we only notify when a bot goes offline or comes back online
        if not any(x.status is discord.Status.offline for x in (before, after)):
            return

        config = self.bot.config.monitored_bots[before.id]
        # we only care about in the notification guild
        key = None
        if config.get('shared_guild'):
            key = before.id
        else:
            if not self.is_shard_presence_guild(before, config['shards']):
                return
            key = (before.id, (before.guild.id >> 22) % config['shards'])

        messagable = self.bot.get_user(config['messagable_id'])
        if messagable is None:
            messagable = self.bot.get_channel(config['messagable_id'])

        status = after.status

        if status is discord.Status.offline:
            msg = f'\N{WARNING SIGN} `{before} {key}` just went offline'
            wait = 30
        else:
            msg = f'\N{PARTY POPPER} `{before} {key}` just came back online'
            wait = 0
            if key in self.pending_messages.keys():
                if self.pending_messages[key].done():  # the task finished already, this must be a new notif?
                    del self.pending_messages[key]
                else:
                    self.pending_messages[key].cancel()
                    del self.pending_messages[key]
                    return

        log.debug(f'Sending notification about {before} ({before.id}) going {status}.')

        now = datetime.datetime.utcnow().strftime('`[%H:%M]`')

        try:
            self.pending_messages[key] = asyncio.get_event_loop().create_task(
                self.send(messagable, f'{now} {msg}', wait)
            )
        except discord.HTTPException:
            pass

    @staticmethod
    async def send(messagable, message, wait=30):
        """sends a message to a messagable after 30 seconds unless cancled"""
        await asyncio.sleep(wait)
        await messagable.send(message)

    def is_shard_presence_guild(self, member: discord.Member, shard_count: int) -> bool:
        """
        Whether the guild the member is part of is significant in terms of presence tracking.
        This is done by calculating if the guild has the lowest of all shared guilds for a specific bot shard
        of the other bot, not ours.
        Parameters
        ----------
        member : discord.Member
            The bot to check the updates significance for.
        shard_count : int
            How many shards the bot has.
        Returns
        -------
        bool
            Whether the update is significant for us.
        """

        shard_id = (member.guild.id >> 22) % shard_count
        guilds = [x for x in self.bot.guilds if x.get_member(member.id) and (x.id >> 22) % shard_count == shard_id]

        if not guilds:
            return False

        return member.guild == min(guilds, key=lambda x: x.id)


def setup(bot):
    bot.add_cog(Bots(bot))
