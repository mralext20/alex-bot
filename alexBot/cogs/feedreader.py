from typing import List
import aiohttp

import discord, feedparser
from discord.ext import commands, tasks

from alexBot.classes import FeedConfig
from alexBot.tools import Cog, get_text




class FeedReader(Cog):
    def __init__(self, bot):
        super().__init__(bot)
        self.feedUpdate.start()

    @tasks.loop(hours=1, reconnect=True)
    async def feedUpdate(self):
        for feedData in self.bot.config.feedPosting:
            async with aiohttp.ClientSession() as session:
                text = await get_text(session, feedData.feedUrl)
                feed = feedparser.parse(text)
                data = await self.bot.db.get_feed_data(f"{feedData.channel}-{feedData.feedUrl}")

                if data != feed.entries[0].id:
                    format = feedData.formatter(feed.entries[0])
                    if isinstance(format, discord.Embed):
                        await self.bot.get_channel(feedData.channel).send(embed=format)
                    else:
                        await self.bot.get_channel(feedData.channel).send(format)
                        
                    await self.bot.db.save_feed_data(f"{feedData.channel}-{feedData.feedUrl}", feed.id)


    def cog_unload(self):
        self.feedUpdate.cancel()


async def setup(bot):
    await bot.add_cog(FeedReader(bot))
