#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

import motor.motor_asyncio
from discord.ext import commands

import config

cogs = ["cogs.admin","cogs.errors","cogs.tags","cogs.utils","cogs.weather"]


class Bot(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(
            command_prefix=('alex!' if os.uname().nodename == 'alexlaptop' else 'a!'),
            **kwargs)

        for cog in cogs:
            try:
                self.load_extension(cog)
            except Exception as e:
                print(f'Could not load extension {cog} due to {e.__class__.__name__}: {e}')

        self.loop.create_task(self.db())

    async def on_ready(self):
        print(f'Logged on as {self.user} (ID: {self.user.id})')

    async def db(self):
        self.mongo = motor.motor_asyncio.AsyncIOMotorClient(config.mongo)
        self.db = self.mongo["alexbot"]
        self.tagsDB = self.db["tags"]
        self.todoDB = self.db["todo"]

bot = Bot()

# write general commands here

bot.run(config.token)
