# -*- coding: utf-8 -*-

import discord
import asyncio_mqtt as aiomqtt
from ..tools import Cog, InteractionPaginator


class HomeAssistantIntigreation(Cog):
    def __init__(self, bot):
        super().__init__(bot)
        self.task = None

    async def mqttLoop(self):
        async with aiomqtt.Client(**self.bot.config.mqttServer) as client:
            async with client.messages() as messages:
                await client.subscribe("alex-bot/#")
                async for message in messages:
                    self.bot.dispatch("ha_update_location", message.topic, message.payload.decode())

    async def cog_load(self):
        self.task = self.bot.loop.create_task(self.mqttLoop())

    async def cog_unload(self):
        self.task.cancel()


async def setup(bot):
    await bot.add_cog(HomeAssistantIntigreation(bot))
