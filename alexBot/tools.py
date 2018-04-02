import json
from logging import getLogger

import aiohttp
from discord.ext import commands

log = getLogger(__name__)

configKeys = {
    "ayy": False,
}


class Cog:
    """ The Cog base class that all cogs should inherit from. """
    def __init__(self, bot):
        self.bot = bot


class BoolConverter(commands.Converter):
    async def convert(self,  ctx, argument):
        if argument[0].lower() == "f":
            return False
        elif argument[0].lower() == "t":
            return True
        else:
            raise commands.BadArgument(f'can not convert {argument} to True or False')


async def get_text(session: aiohttp.ClientSession, url) -> str:
    # log.debug(f"fetched url: {url}")
    async with session.get(url) as content:
        return await content.text()


async def get_json(session: aiohttp.ClientSession, url) -> dict:
    # log.debug(f"fetched json: {url}")
    async with session.get(url) as content:
        return await content.json()


async def haste(session: aiohttp.ClientSession, text: str, extension: str = "py") -> str:
    """ Pastes something to Hastebin, and returns the link to it. """
    async with session.post('https://hastebin.com/documents', data=text) as resp:
        resp_json = await resp.json()
        ret = f"https://hastebin.com/{resp_json['key']}.{extension}"
        log.info(f"hasted, return was {ret}")
        return ret


async def create_guild_config(bot, guild_id: int) -> dict:
    log.info(f'creating a guild config for {guild_id}')
    cfg = json.dumps(configKeys)
    await bot.pool.execute("""INSERT INTO configs (id, data, type) VALUES ($1, $2, 'guild')""", guild_id, cfg)
    return configKeys


async def get_guild_config(bot, guild_id: int) -> dict:
    ret = {}
    try:
        ret = bot.configs[guild_id]

    except KeyError:
        ret = await bot.pool.fetchrow("""SELECT data FROM configs WHERE id=$1 AND type='guild'""", guild_id)
        if ret is None:
            ret = await create_guild_config(bot, guild_id)
        else:
            ret = json.loads(ret['data'])
    finally:
        ret = {**configKeys, **ret}
        bot.configs[guild_id] = ret
    return ret


async def update_guild_key(bot, guild_id: int, key: str, value):
    """updates the `key` to be `value`.
    note: this method is extremely dumb,
    as it does no error checking to ensure that you are giving it the right value for a key."""
    bot.configs[guild_id][key] = value
    cfg = json.dumps(bot.configs[guild_id])
    await bot.pool.execute("""UPDATE configs SET data=$1 WHERE id=$2""", cfg, guild_id)
