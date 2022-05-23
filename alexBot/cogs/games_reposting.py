import logging
from typing import TYPE_CHECKING, Dict

import discord
from discord.message import Message
from discord.webhook import WebhookMessage

from ..tools import Cog

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from bot import Bot


class GamesReposting(Cog):
    def __init__(self, bot: "Bot"):
        super().__init__(bot)
        self.linked: Dict[int, WebhookMessage] = {}

    @Cog.listener()
    async def on_ready(self):
        self.webhook = discord.Webhook.from_url(self.bot.config.nerdiowo_announcements_webhook, session=self.bot.session)
        

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.channel == discord.DMChannel:
            return
        if message.channel.category_id == 896853287108759615:
            additional_content = [await x.to_file() for x in message.attachments]

            msg = await self.webhook.send(
                content=message.system_content if message.is_system else message.content,
                wait=True,
                username=message.author.name,
                avatar_url=message.author.avatar_url,
                files=additional_content,
                embeds=message.embeds,
                allowed_mentions=discord.AllowedMentions.none(),
            )

            self.linked[message.id] = msg

    @Cog.listener()
    async def on_message_edit(self, before: Message, after: Message):
        if before.id in self.linked:
            if before.content != after.content:
                await self.linked[before.id].edit(content=after.content)


async def setup(bot):
    await bot.add_cog(GamesReposting(bot))
