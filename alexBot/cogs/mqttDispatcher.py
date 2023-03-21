# -*- coding: utf-8 -*-

import asyncio
import logging
import asyncio_mqtt as aiomqtt

from ..tools import Cog

log = logging.getLogger(__name__)


class HomeAssistantIntigreation(Cog):
    def __init__(self, bot):
        super().__init__(bot)
        self.task: asyncio.Task = None

    async def mqttLoop(self):
        while True:
            try:
                async with aiomqtt.Client(**self.bot.config.mqttServer) as client:
                    async with client.messages() as messages:
                        await client.subscribe("alex-bot/#")
                        async for message in messages:
                            if message.topic.matches("alex-bot/location/#"):
                                self.bot.dispatch(
                                    "ha_update_location", message.topic.value.split('/')[2], message.payload.decode()
                                )
                            if message.topic.matches("alex-bot/vcControl/#"):
                                self.bot.dispatch(
                                    "ha_vc_control", message.topic.value.split('/')[2], message.payload.decode()
                                )
            except aiomqtt.MqttError as error:
                log.error(f"MQTT error: {error}, retrying in 5 minutes")
                await asyncio.sleep(5 * 60)

    async def mqttPublish(self, topic, payload):
        async with aiomqtt.Client(**self.bot.config.mqttServer) as client:
            await client.publish(topic, payload)

    async def cog_load(self):
        self.task = self.bot.loop.create_task(self.mqttLoop())

    async def cog_unload(self):
        self.task.cancel()


async def setup(bot):
    await bot.add_cog(HomeAssistantIntigreation(bot))
