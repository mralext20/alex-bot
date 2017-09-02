#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

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

    async def on_ready(self):
        print(f'Logged on as {self.user} (ID: {self.user.id})')



bot = Bot()

# write general commands here

bot.run(config.token)
