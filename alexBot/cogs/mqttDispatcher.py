# -*- coding: utf-8 -*-

import asyncio
import logging
from typing import Optional
from urllib.parse import urlparse

import aiomqtt

from ..tools import Cog

log = logging.getLogger(__name__)


class HomeAssistantIntigreation(Cog):
    def __init__(self, bot):
        super().__init__(bot)
        self.task: asyncio.Task = None
        self.active_client: Optional[aiomqtt.Client] = None

    async def mqttLoop(self):
        while True:
            try:
                url = urlparse(self.bot.config.mqtt_url)
                async with aiomqtt.Client(
                    hostname=url.hostname, username=url.username, password=url.password, port=url.port
                ) as client:
                    self.active_client = client
                    await client.subscribe("alex-bot/#")
                    async for message in client.messages:
                        if message.topic.matches("alex-bot/location/#"):
                            self.bot.dispatch(
                                "ha_update_location", message.topic.value.split('/')[2], message.payload.decode()
                            )
                        if message.topic.matches("alex-bot/vcControl/#"):
                            self.bot.dispatch(
                                "ha_vc_control", int(message.topic.value.split('/')[2]), message.payload.decode()
                            )

            except aiomqtt.MqttError as error:
                log.error(f"MQTT error: {error}, retrying in 5 minutes")
                await asyncio.sleep(5 * 60)
            finally:
                self.active_client = None

    async def mqttPublish(self, topic, payload, qos=1, retain=True):
        if self.active_client:
            await self.active_client.publish(topic, payload, qos=qos, retain=retain)
        else:
            raise aiomqtt.MqttError("No active MQTT client")

    async def cog_load(self):

        self.task = self.bot.loop.create_task(self.mqttLoop())

    async def cog_unload(self):
        self.task.cancel()


async def setup(bot):
    if not bot.config.mqtt_url:
        log.warning("No MQTT URL provided, MQTT integration will not be enabled")
        return
    await bot.add_cog(HomeAssistantIntigreation(bot))
