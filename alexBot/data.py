import dataclasses
import json
from typing import List, Optional

import aiosqlite

from alexBot.classes import ButtonRole, ButtonType, FeedConfig, GuildData, MovieSuggestion, RecurringReminder, UserData

from .tools import Cog


class Data(Cog):
    async def get_guild_data(self, guildId: int) -> GuildData:
        """
        used to retrive a GuildData from the database. see save_guild_data to save it back.
        """
        async with aiosqlite.connect(self.bot.config.db or 'configs.db') as conn:
            async with conn.execute("SELECT data FROM guilds WHERE guildId=?", (guildId,)) as cur:
                data = await cur.fetchone()
                if not data:
                    return GuildData()
                raw = json.loads(data[0])
                return GuildData.from_dict(raw)

    async def save_guild_data(self, guildId: int, data: GuildData):
        async with aiosqlite.connect(self.bot.config.db or 'configs.db') as conn:
            await conn.execute(
                "REPLACE INTO guilds (guildId, data) VALUES (?,?)", (guildId, json.dumps(dataclasses.asdict(data)))
            )
            await conn.commit()

    async def get_user_data(self, userId: int) -> UserData:
        """
        used to retrive a GuildData from the database. see save_guild_data to save it back.
        """
        async with aiosqlite.connect(self.bot.config.db or 'configs.db') as conn:
            async with conn.execute("SELECT data FROM users WHERE userId=?", (userId,)) as cur:
                data = await cur.fetchone()
                if not data:
                    return UserData()
                raw = json.loads(data[0])
                return UserData.from_dict(raw)

    async def save_user_data(self, userId: int, data: UserData):
        async with aiosqlite.connect(self.bot.config.db or 'configs.db') as conn:
            await conn.execute(
                "REPLACE INTO users (userId, data) VALUES (?,?)", (userId, json.dumps(dataclasses.asdict(data)))
            )
            await conn.commit()

    async def get_feeds(self) -> List[FeedConfig]:
        """
        fetch all feeds
        """
        async with aiosqlite.connect(self.bot.config.db or 'configs.db') as conn:
            async with conn.execute("SELECT data FROM rssFeeds") as cur:
                data = await cur.fetchall()
                feeds = []
                for row in data:
                    feeds.append(FeedConfig(**json.loads(row[0])))
                return feeds

    async def save_feeds(self, feeds: List[FeedConfig]):
        """
        deletes all feeds, then saves the all of them again
        """
        async with aiosqlite.connect(self.bot.config.db or 'configs.db') as conn:
            await conn.execute("DELETE FROM rssFeeds")
            for feed in feeds:
                await conn.execute("INSERT INTO rssFeeds (data) VALUES (?)", (json.dumps(dataclasses.asdict(feed)),))
            await conn.commit()

    async def get_feed_data(self, feedId: str) -> Optional[int]:
        """
        used to get the latest feed entry ID from the database. see save_feed_data to save it back.
        """
        async with aiosqlite.connect(self.bot.config.db or 'configs.db') as conn:
            async with conn.execute("SELECT data FROM rssFeedLastPosted WHERE channelfeed=?", (feedId,)) as cur:
                data = await cur.fetchone()
                if not data:
                    return None
                return int(data[0])

    async def save_feed_data(self, feedId: str, data: int):
        async with aiosqlite.connect(self.bot.config.db or 'configs.db') as conn:
            await conn.execute("REPLACE INTO rssFeedLastPosted (channelfeed, data) VALUES (?,?)", (feedId, str(data)))
            await conn.commit()

    async def get_roles_data(self) -> List[ButtonRole]:
        """
        fetch all roles for a givin guild
        """
        async with aiosqlite.connect(self.bot.config.db or 'configs.db') as conn:
            async with conn.execute("SELECT data FROM buttonRoles") as cur:
                data = await cur.fetchall()
                roles = []
                for row in data:
                    roles.append(ButtonRole(**json.loads(row[0])))
                if not data:
                    return []
                for role in roles:
                    role.type = ButtonType(role.type)
                return roles

    async def save_roles_data(self, data: List[ButtonRole]):
        """
        deletes all roles, then saves the all of them again
        """
        async with aiosqlite.connect(self.bot.config.db or 'configs.db') as conn:
            await conn.execute("DELETE FROM buttonRoles")
            for role in data:
                await conn.execute("INSERT INTO buttonRoles (data) VALUES (?)", (json.dumps(dataclasses.asdict(role)),))
            await conn.commit()

    async def get_movies_data(self) -> List[MovieSuggestion]:
        """
        fetch all movies for a givin guild
        """
        async with aiosqlite.connect(self.bot.config.db or 'configs.db') as conn:
            async with conn.execute("SELECT data FROM movieSuggestions") as cur:
                data = await cur.fetchall()
                movies = []
                for row in data:
                    movies.append(MovieSuggestion(**json.loads(row[0])))
                if not data:
                    return []
                return movies

    async def save_movies_data(self, data: List[MovieSuggestion]):
        """
        deletes all movies, then saves the all of them again
        """
        async with aiosqlite.connect(self.bot.config.db or 'configs.db') as conn:
            await conn.execute("DELETE FROM movieSuggestions")
            for movie in data:
                await conn.execute(
                    "INSERT INTO movieSuggestions (data) VALUES (?)", (json.dumps(dataclasses.asdict(movie)),)
                )
            await conn.commit()

    async def get_recurring_reminders(self):
        async with aiosqlite.connect(self.bot.config.db or 'configs.db') as conn:
            async with conn.execute("SELECT data FROM recurringReminders") as cur:
                data = await cur.fetchall()
                reminders = []
                for row in data:
                    reminders.append(RecurringReminder(**json.loads(row[0])))
                if not data:
                    return []
                return reminders

    async def save_recurring_reminders(self, reminders: List[RecurringReminder]):
        async with aiosqlite.connect(self.bot.config.db or 'configs.db') as conn:
            await conn.execute("DELETE FROM recurringReminders")
            for reminder in reminders:
                await conn.execute(
                    "INSERT INTO recurringReminders (data) VALUES (?)", (json.dumps(dataclasses.asdict(reminder)),)
                )
            await conn.commit()


async def setup(bot):
    await bot.add_cog(Data(bot))
    bot.db = bot.get_cog('Data')
