import aiohttp
import motor.motor_asyncio as mongo

DEFAULT_CONFIG = {"CURRENCY": False}

class Cog:
    """ The Cog baseclass that all cogs should inherit from. """
    def __init__(self, bot):
        self.bot = bot


async def get_text(session:aiohttp.ClientSession, url) -> str:
    async with session.get(url) as content:
        text = await content.text()
        return text


async def haste(session: aiohttp.ClientSession, text: str, extension:str="py") -> str:
    """ Pastes something to Hastebin, and returns the link to it. """
    async with session.post('https://hastebin.com/documents', data=text) as resp:
        resp_json = await resp.json()
        return f"https://hastebin.com/{resp_json['key']}.{extension}"


async def get_config(configs: mongo.AsyncIOMotorCollection, id:int):
    obj = await configs.find_one({"ID":id})
    if obj is None:
        conf = {"ID":id}
        conf.update(DEFAULT_CONFIG)
        return await configs.insert_one(conf)
    else:
        return obj

async def get_config_value(configs:mongo.AsyncIOMotorCollection, id:int, key:str):
    config = await get_config(configs, id)
    return config[key]