import logging
from typing import Dict

import discord
from discord import PartialEmoji
from discord.ext import commands
from discord.message import Message
from discord.webhook import AsyncWebhookAdapter, WebhookMessage
from emoji_data import EmojiSequence

from ..tools import Cog

log = logging.getLogger(__name__)


class GamesReposting(Cog):
    def __init__(self, bot: "Bot"):
        super().__init__(bot)
        self.linked: Dict[int, WebhookMessage] = {}
        self.webhook = discord.Webhook.from_url(
            self.bot.config.nerdiowo_announcements_webhook, adapter=AsyncWebhookAdapter(session=self.bot.session)
        )

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.channel.category_id == 896853287108759615:
            additional_content = [await x.to_file() for x in message.attachments]

            msg = await self.webhook.send(
                content=message.content,
                wait=True,
                username=message.author.name,
                avatar_url=message.author.avatar_url,
                files=additional_content,
                embeds=message.embeds,
            )

            self.linked[message.id] = msg

    @Cog.listener()
    async def on_message_edit(self, before: Message, after: Message):
        if before.id in self.linked:
            if before.content != after.content:
                await self.linked[before.id].edit(content=after.content)


def setup(bot):
    bot.add_cog(GamesReposting(bot))
