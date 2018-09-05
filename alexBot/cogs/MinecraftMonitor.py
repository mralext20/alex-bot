# -*- coding: utf-8 -*-
import asyncio

from ..tools import Cog
import discord
from discord.ext import commands
from mcstatus import MinecraftServer

import logging

log = logging.getLogger(__name__)



class MinecraftMonitor(Cog):
    """allows you to track a minecraft server's players.
     you can only monitor one server per channel. requires manage channel permissions."""
    def __init__(self, bot):
        super().__init__(bot)
        self.minecraftServerPairs = {}
        self.lastStates = {}
        self.bot.loop.create_task(self.startup())

    async def startup(self):
        existing = await self.bot.pool.fetch("""SELECT * FROM minecraft""")
        self.minecraftServerPairs = {i['channel']: i['server'] for i in existing}
        self.lastStates = {}  # server : list of players?
        self.bot.loop.create_task(self.monitor())

    async def monitor(self):
        await asyncio.sleep(5)
        2 == 2
        while not self.bot.is_closed():
            if not self.bot.minecraft:
                log.debug('stoping minecraft checks')
                break
            log.debug('checking minecraft...')
            for channel, server in self.minecraftServerPairs.items():
                state = await self.bot.loop.run_in_executor(None, self.fetch_players, server)
                if state is None:
                    continue
                try:
                    changed = state != self.lastStates[server]
                except KeyError:
                    changed = False
                    self.lastStates[server] = state
                if changed:
                    if len(state) > 0:
                        msg = f"Members in minecraft are {', '.join(state)}"
                    else:
                        msg = "everyone has left minecraft."
                    await self.bot.get_channel(channel).send(self.bot.clean_content(msg))
                    self.lastStates[server] = state
            log.debug('done checking minecraft')

            await asyncio.sleep(60)

    def fetch_players(self, server):
        try:
            s = MinecraftServer(server)
            players = s.status().players.sample
            if players is None:
                return set()
            return {i.name for i in players}
        except ConnectionRefusedError:
            pass

    @commands.command()
    @commands.is_owner()
    async def addServerMonitor(self, ctx, server):
        """adds a server to be tracked. """

        channel = ctx.channel.id
        await self.bot.pool.execute("""INSERT INTO minecraft (channel, server) VALUES ($1, $2)""", channel, server)
        self.minecraftServerPairs[channel] = server

def setup(bot):
    bot.add_cog(MinecraftMonitor(bot))
