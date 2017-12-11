import aiohttp
from asyncpg.pool import Pool
import logging
import json

log = logging.getLogger(__name__)

configKeys = {
    "money": False
}


class Cog:
    """ The Cog baseclass that all cogs should inherit from. """

    def __init__(self, bot):
        self.bot = bot


async def get_text(session: aiohttp.ClientSession, url) -> str:
    log.debug(f"fetched url: {url}")
    async with session.get(url) as content:
        return await content.text()


async def get_json(session: aiohttp.ClientSession, url) -> dict:
    log.debug(f"fetched json: {url}")
    async with session.get(url) as content:
        return await content.json()


async def haste(session: aiohttp.ClientSession, text: str, extension: str = "py") -> str:
    """ Pastes something to Hastebin, and returns the link to it. """
    async with session.post('https://hastebin.com/documents', data=text) as resp:
        resp_json = await resp.json()
        ret = f"https://hastebin.com/{resp_json['key']}.{extension}"
        log.debug(f"hasted, return was {ret}")
        return ret


async def create_guild_config(pool: Pool, guild_id: int) -> dict:
    cfg = json.dumps(configKeys)
    await pool.execute("""INSERT INTO configs (id, data, type) VALUES ($1, $2, 'guild')""", guild_id, cfg)
    return await get_guild_config(pool, guild_id)


async def get_guild_config(pool: Pool, guild_id: int) -> dict:
    ret = await pool.fetchrow("""SELECT data FROM configs WHERE id=$1 AND type='guild'""", guild_id)
    if ret is None:
        return await create_guild_config(pool, guild_id)
    ret = json.loads(ret[0])
    return ret
