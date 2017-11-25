import aiohttp
import json

import logging

log = logging.getLogger(__name__)

class Cog:
    """ The Cog baseclass that all cogs should inherit from. """
    def __init__(self, bot):
        self.bot = bot


async def get_text(session:aiohttp.ClientSession, url) -> str:
    log.debug(f"fetched url: {url}")
    async with session.get(url) as content:
        return await content.text()


async def get_json(session:aiohttp.ClientSession, url) -> dict:
    log.debug(f"fetched json: {url}")
    async with session.get(url) as content:
        return await content.json()


async def haste(session: aiohttp.ClientSession, text: str, extension:str="py") -> str:
    """ Pastes something to Hastebin, and returns the link to it. """
    async with session.post('https://hastebin.com/documents', data=text) as resp:
        resp_json = await resp.json()
        ret = f"https://hastebin.com/{resp_json['key']}.{extension}"
        log.debug(f"hasted, return was {ret}")
        return ret