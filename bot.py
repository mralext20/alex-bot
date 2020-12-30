#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
from pathlib import Path

import aiohttp
import aiosqlite
import discord
from discord.ext import commands

import config
from alexBot.channel_logging import setup_logging

from alexBot.tools import metar_only_in_vasa

cogs = [x.stem for x in Path('alexBot/cogs').glob('*.py') if x.stem != "__init__"]

log = logging.getLogger(__name__)


intents = discord.Intents.default()
intents.members = True
intents.presences = True


class Bot(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(
            command_prefix=config.prefix, intents=intents, **kwargs)
        self.session = None
        self.loop.create_task(self._asyncinit())
        self.logger = logging.getLogger("bot")
        self.config: config = config
        self.db: aiosqlite.Connection = None
        self.configs = {}
        self.location = config.location
        self.owner = None
        logging.getLogger('discord.gateway').setLevel(logging.ERROR)
        self.loop.create_task(self.cogSetup())
        self.minecraft = True

    async def on_ready(self):
        log.info(f'Logged on as {self.user} ({self.user.id})')
        self.owner = (await self.application_info()).owner
        log.info(f'owner is {self.owner} ({self.owner.id})')
        self.add_check(metar_only_in_vasa)
        self.session = aiohttp.ClientSession()

    async def _asyncinit(self):
        self.db = await aiosqlite.connect('configs.db', loop=self.loop)

    async def cogSetup(self):
        while self.db is None:
            log.info('waiting for initialization of async connectors...')
            await asyncio.sleep(.5)
        for cog in cogs:
            try:
                self.load_extension(f"alexBot.cogs.{cog}")
                log.info(f'loaded {cog}')
            except Exception as e:
                log.error(f'Could not load extension {cog} due to {e.__class__.__name__}: {e}')

    @staticmethod
    def clean_mentions(content):
        content = content.replace('`', '\'')
        content = content.replace('@', '@\u200b')
        content = content.replace('&', '&\u200b')
        content = content.replace('<#', '<#\u200b')
        return content

    @staticmethod
    def clean_formatting(content):
        content = content.replace('_', '\\_')
        content = content.replace('*', '\\*')
        content = content.replace('`', '\\`')
        return content

    def clean_clean(self, content):
        content = self.clean_mentions(content)
        content = self.clean_formatting(content)
        return content

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        else:
            await self.process_commands(message)

    async def on_command(self, ctx):
        # thanks dogbot ur a good
        content = ctx.message.content
        content = self.clean_mentions(content)

        author = ctx.message.author
        guild = ctx.guild
        checks = [c.__qualname__.split('.')[0] for c in ctx.command.checks]
        location = '[DM]' if isinstance(ctx.channel, discord.DMChannel) else \
            f'[Guild {guild.name} {guild.id}]'

        log.info('%s [cmd] %s(%d) "%s" checks=%s', location, author,
                 author.id, content, ','.join(checks) or '(none)')


loop = asyncio.get_event_loop()

webhooks = {}
session = aiohttp.ClientSession()

for name in config.logging:
    level = getattr(logging, name.upper(), None)
    if level is None:
        continue

    url = config.logging[name]
    webhooks[level] = discord.Webhook.from_url(url, adapter=discord.AsyncWebhookAdapter(session))

with setup_logging(webhooks=webhooks):
    bot = Bot()
    bot.load_extension('jishaku')
    try:
        loop.run_until_complete(bot.start(config.token))
    except KeyboardInterrupt:
        loop.run_until_complete(bot.close())
        loop.run_until_complete(bot.db.close())
        loop.run_until_complete(session.close())
