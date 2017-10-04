import aiohttp


class Cog:
    """ The Cog baseclass that all cogs should inherit from. """
    def __init__(self, bot):
        self.bot = bot


async def get_text(session:aiohttp.ClientSession, url) -> str:
    async with session.get(url) as content:
        text = await content.text()
        return text