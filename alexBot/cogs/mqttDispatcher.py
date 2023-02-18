# -*- coding: utf-8 -*-

import asyncio_mqtt as aiomqtt
import discord

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
                    if message.topic.matches("alex-bot/location/#"):
                        self.bot.dispatch(
                            "ha_update_location", message.topic.value.split('/')[2], message.payload.decode()
                        )
                    if message.topic.matches("alex-bot/vcControl/#"):
                        self.bot.dispatch("ha_vc_control", message.topic.value.split('/')[2], message.payload.decode())

    async def cog_load(self):
        self.task = self.bot.loop.create_task(self.mqttLoop())

    async def cog_unload(self):
        self.task.cancel()


async def setup(bot):
    await bot.add_cog(HomeAssistantIntigreation(bot))
