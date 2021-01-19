import dataclasses

import json
from .tools import Cog
import aiosqlite
from alexBot.classes import GuildData, UserData


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

    async def save_guild_data(self, guildId, data: GuildData):
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

    async def save_user_data(self, userId, data: UserData):
        async with aiosqlite.connect(self.bot.config.db or 'configs.db') as conn:
            await conn.execute(
                "REPLACE INTO users (userId, data) VALUES (?,?)", (userId, json.dumps(dataclasses.asdict(data)))
            )
            await conn.commit()


def setup(bot):
    bot.add_cog(Data(bot))
    bot.db = bot.get_cog('Data')
