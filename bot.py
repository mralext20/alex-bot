#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

import asyncpg
from discord.ext import commands

import config


class Bot(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(
            command_prefix=('alex!' if os.uname().nodename == 'alexlaptop' else 'a!'),
            **kwargs)

        for cog in config.cogs:
            try:
                self.load_extension(cog)
            except Exception as e:
                print(f'Could not load extension {cog} due to {e.__class__.__name__}: {e}')

        self.loop.create_task(self.db())

    async def on_ready(self):
        print(f'Logged on as {self.user} (ID: {self.user.id})')

    async def db(self):
        try:
            self.db = await asyncpg.create_pool(config.dsn, loop=self.loop)
        except Exception:
            print('Could not connect to DB')


bot = Bot()

# write general commands here

bot.run(config.token)
