import logging
from typing import TYPE_CHECKING, Dict, Optional

import aiohttp
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
        self.session: Optional[aiohttp.ClientSession] = None

    async def cog_unload(self):
        await self.session.close()

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if not isinstance(message.channel, discord.TextChannel):
            return
        if message.channel.category_id == 896853287108759615:
            if not self.session:
                self.session = aiohttp.ClientSession()

            wh = discord.Webhook.from_url(self.bot.config.nerdiowo_announcements_webhook, session=self.session)
            additional_content = [await x.to_file() for x in message.attachments]

            msg = await wh.send(
                content=message.system_content or '',
                wait=True,
                username=message.author.name,
                avatar_url=message.author.display_avatar.url,
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
