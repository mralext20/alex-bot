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

        messagable = self.bot.get_user(config['owner_id'])
        if messagable is None:
            messagable = self.bot.get_channel(config['owner_id'])

        shard_count = config.get('shard_count', 1)

        if not self.is_shard_presence_guild(before, shard_count):
            return

        status = after.status
        shard_id = (before.guild.id >> 22) % shard_count

        if status is discord.Status.offline:
            msg = f'\N{WARNING SIGN} `{before} {before.id}` shard `{shard_id}/{shard_count}` just went offline'
            wait = 30
        else:
            msg = f'\N{PARTY POPPER} `{before} {before.id}` shard `{shard_id}/{shard_count}` just came back online'
            wait = 0
            if (before.id in self.pending_messages.keys()):
                self.pending_messages[before.id].cancel()
                return

        log.debug(f'Sending notification about {before} {before.id} shard {shard_id}/{shard_count} going {status}.')

        now = datetime.datetime.utcnow().strftime('`[%H:%M]`')

        try:
            self.pending_messages[before.id] = asyncio.create_task(self.send(messagable, f'{now} {msg}', wait))
        except discord.HTTPException:
            pass

    async def send(messagable: discord.abc.messagable, message, wait=30):
        """sends a message to a messagable after 30 seconds unless cancled"""
        await asyncio.sleep(wait)
        await messagable.send(message)

    def is_shard_presence_guild(self, member, shard_count):
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
