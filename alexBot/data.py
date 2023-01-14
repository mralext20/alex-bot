import dataclasses
import json
from typing import List, Optional

import aiosqlite

from alexBot.classes import ButtonRole, ButtonType, GuildData, UserData

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


async def setup(bot):
    await bot.add_cog(Data(bot))
    bot.db = bot.get_cog('Data')
