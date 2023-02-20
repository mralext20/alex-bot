import asyncio
import datetime
import re
from time import mktime
from typing import List, Optional

import aiohttp
import discord
import feedparser
from discord.ext import commands, tasks

from alexBot.classes import FeedConfig
from alexBot.tools import Cog, get_text

times = [datetime.time(hour=hour, minute=5, tzinfo=datetime.timezone.utc) for hour in range(0, 24, 1)]
extractYoutubeId = re.compile(r'"externalId":"([a-zA-Z_0-9]+)"')

FORUMCHANNEL_ID = 1054582714495414343


class FeedReader(Cog):
    def __init__(self, bot):
        super().__init__(bot)
        self.feedUpdate.start()
        self.tags = None

    feedGroup = discord.app_commands.Group(
        name="feed",
        description="nerdiowo feeds menu",
        guild_ids=[791528974442299412],
    )

    @tasks.loop(reconnect=True, time=times)
    async def feedUpdate(self):
        forumChannel: discord.ForumChannel = self.bot.get_channel(1054582714495414343)
        feeds = await self.bot.db.get_feeds()
        for feedData in feeds:
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

    @feedGroup.command(name="nerdiowofeed", description="Add a feed to the nerdiowo FeedChannel")
    async def nerdiowoFeed(self, interaction: discord.Interaction, feedUrl: str, tag: Optional[discord.ForumTag]):
        feeds = await self.bot.db.get_feeds()
        if 'youtube' in feedUrl:
            # youtube channel, need to convert to rss
            async with aiohttp.ClientSession() as session:
                text = await get_text(session, feedUrl)
                channel_id = extractYoutubeId.finditer(text).__next__().group(1)
                feedUrl = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

        if feedUrl in [feed.feedUrl for feed in feeds]:
            await interaction.response.send_message("Feed already added!", ephemeral=True)
            return
        async with aiohttp.ClientSession() as session:
            text = await get_text(session, feedUrl)
            try:
                feed = feedparser.parse(text)
            except Exception as e:
                await interaction.response.send_message("Invalid feed!", ephemeral=True)
                return
        feeds.append(FeedConfig(tag.id if tag is not None else None, feedUrl))
        await self.bot.db.save_feeds(feeds)
        await interaction.response.send_message("Feed added!", ephemeral=True)

    @feedGroup.command(name="removeFeed", description="Remove a feed from the nerdiowo FeedChanel")
    async def removeFeed(self, interaction: discord.Interaction, feedUrl: str):
        feeds = await self.bot.db.get_feeds()
        if feedUrl not in [feed.feedUrl for feed in feeds]:
            await interaction.response.send_message("Feed not found!", ephemeral=True)
            return
        feeds = [feed for feed in feeds if feed.feedUrl != feedUrl]
        await self.bot.db.save_feeds(feeds)
        await interaction.response.send_message("Feed removed!", ephemeral=True)

    @removeFeed.autocomplete('feedUrl')
    async def removeFeed_autocomplete(
        self, interaction: discord.Interaction, guess: str
    ) -> List[discord.app_commands.Choice]:
        feeds = await self.bot.db.get_feeds()
        return [
            discord.app_commands.Choice(name=feed.feedUrl, value=feed.feedUrl)
            for feed in feeds
            if guess in feed.feedUrl
        ]

    @nerdiowoFeed.autocomplete('tag')
    async def nerdiowoFeed_autocomplete(
        self, interaction: discord.Interaction, guess: str
    ) -> List[discord.app_commands.Choice]:
        c: discord.ForumChannel = interaction.guild.get_channel(FORUMCHANNEL_ID)
        if self.tags is None:
            tags = c.available_tags
            self.tags = tags

        return [
            discord.app_commands.Choice(name=tag.name, value=tag.id) for tag in self.tags if tag.name.startswith(guess)
        ]

    @feedUpdate.before_loop
    async def before_feedUpdate(self):
        await self.bot.wait_until_ready()

    def cog_unload(self):
        self.feedUpdate.cancel()


async def setup(bot):
    await bot.add_cog(FeedReader(bot))
