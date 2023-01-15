import asyncio
import datetime
from time import mktime
from typing import List

import aiohttp
import discord
import feedparser
from discord.ext import commands, tasks

from alexBot.classes import FeedConfig
from alexBot.tools import Cog, get_text

times = [datetime.time(hour=hour, minute=2, tzinfo=datetime.timezone.utc) for hour in range(0, 24, 1)]


class FeedReader(Cog):
    def __init__(self, bot):
        super().__init__(bot)
        self.feedUpdate.start()

    @tasks.loop(reconnect=True, time=times)
    async def feedUpdate(self):
        forumChannel: discord.ForumChannel = self.bot.get_channel(1063907139715874896)
        for feedData in self.bot.config.feedPosting:
            async with aiohttp.ClientSession() as session:
                text = await get_text(session, feedData.feedUrl)
                feed = feedparser.parse(text)
                lastPostedStamp = await self.bot.db.get_feed_data(feedData.feedUrl)

                if lastPostedStamp != mktime(feed.entries[0].published_parsed):
                    if lastPostedStamp is None:  # handle new feeds
                        try:
                            lastPostedStamp = mktime(feed.entries[1].published_parsed)
                        except IndexError:
                            if len(feed.entries) == 0:
                                await self.bot.db.save_feed_data(feedData.feedUrl, None)
                            else:  # one entry?
                                await forumChannel.create_thread(
                                    name=f"{feed.feed.title}  -  {self.bot.clean_clean(feed.entries[0].title)}"[:100],
                                    content=f"{entry.link}\n\n{self.bot.clean_clean(feed.entries[0].summary[:500])}",
                                    applied_tags=[forumChannel.get_tag(feedData.tagId)]
                                    if feedData.tagId is not None
                                    else [],
                                )
                                await self.bot.db.save_feed_data(
                                    feedData.feedUrl, int(mktime(feed.entries[0].published_parsed))
                                )
                    #  there's new posts!
                    # ... how many?
                    # loop over the entries until we find our last post!
                    for entry in feed.entries:
                        if int(mktime(entry.published_parsed)) <= lastPostedStamp:
                            break
                        else:
                            await forumChannel.create_thread(
                                name=f"{feed.feed.title}  -  {self.bot.clean_clean(entry.title)}"[:100],
                                content=f"{entry.link}\n\n{self.bot.clean_clean(feed.entries[0].summary[:500])}",
                                applied_tags=([forumChannel.get_tag(feedData.tagId)])
                                if feedData.tagId is not None
                                else [],
                            )

                    await self.bot.db.save_feed_data(feedData.feedUrl, int(mktime(feed.entries[0].published_parsed)))

    @feedUpdate.before_loop
    async def before_feedUpdate(self):
        await self.bot.wait_until_ready()

    def cog_unload(self):
        self.feedUpdate.cancel()


async def setup(bot):
    await bot.add_cog(FeedReader(bot))
