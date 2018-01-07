#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
import os
from pathlib import Path

import aiohttp
import asyncpg
import discord
from discord.ext import commands

import config
from alexBot.channel_logging import setup_logging

cogs = [x.stem for x in Path('alexBot/cogs').glob('*.py') if x.stem != "__init__"]

if not config.money['enabled']:
    cogs.remove('money')

log = logging.getLogger(__name__)


class Bot(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(
            command_prefix=('alex!' if os.uname().nodename == 'alexlaptop' else 'a!'),
            **kwargs)
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.logger = logging.getLogger("bot")
        self.config = config
        self.pool = None
        self.configs = {}
        self.wallets = {}
        self.location = ('laptop' if os.uname().nodename == 'alexlaptop' else 'pi')

        for cog in cogs:
            try:
                self.load_extension(f"alexBot.cogs.{cog}")
                log.info(f'loaded {cog}')
            except Exception as e:
                log.error(f'Could not load extension {cog} due to {e.__class__.__name__}: {e}')

        self.loop.create_task(self._pool())

    async def on_ready(self):
        log.info(f'Logged on as {self.user} (ID: {self.user.id})')

    async def _pool(self):
        self.pool = await asyncpg.create_pool(config.dsn, loop=self.loop)

    def clean_content(self, content):
        content = content.replace('`', '\'')
        content = content.replace('@', '@\u200b')
        content = content.replace('&', '&\u200b')
        content = content.replace('<#', '<#\u200b')
        return content

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        else:
            await self.process_commands(message)

    async def on_command(self, ctx):
        # thanks dogbot ur a good
        content = ctx.message.content
        content = self.clean_content(content)

        author = ctx.message.author
        guild = ctx.guild
        checks = [c.__qualname__.split('.')[0] for c in ctx.command.checks]
        location = '[DM]' if isinstance(ctx.channel, discord.DMChannel) else \
            f'[Guild {guild.name} {guild.id}]'

        log.info('%s [cmd] %s(%d) "%s" checks=%s', location, author,
                 author.id, content, ','.join(checks) or '(none)')


loop = asyncio.get_event_loop()

webhooks = {}
session = aiohttp.ClientSession(loop=loop)

for name in config.logging:
    level = getattr(logging, name.upper(), None)
    if level is None:
        continue

    url = config.logging[name]
    webhooks[level] = discord.Webhook.from_url(url, adapter=discord.AsyncWebhookAdapter(session))

with setup_logging(webhooks=webhooks):
    bot = Bot()
    bot.run(config.token)
