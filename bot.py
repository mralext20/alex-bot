#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

import asyncpg
from discord.ext import commands
import aiohttp
import config

import logging

cogs = ["admin", "errors", "tags", "utils", "weather", "fun"]

logging.basicConfig(level=logging.INFO)


class Bot(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(
            command_prefix=('alex!' if os.uname().nodename == 'alexlaptop' else 'a!'),
            **kwargs)
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.logger = logging.getLogger("bot")
        self.config = config
        self.pool = None

        for cog in cogs:
            try:
                self.load_extension(f"alexBot.cogs.{cog}")
            except Exception as e:
                print(f'Could not load extension {cog} due to {e.__class__.__name__}: {e}')

        self.loop.create_task(self._pool())

    async def on_ready(self):
        print(f'Logged on as {self.user} (ID: {self.user.id})')

    async def _pool(self):
        self.pool = await asyncpg.create_pool(config.dsn, loop=self.loop)


bot = Bot()

# write general commands here

bot.run(config.token)
