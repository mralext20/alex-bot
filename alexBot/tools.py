from functools import wraps
import time

from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from bot import Bot

from logging import getLogger

import aiohttp
import xmltodict
from discord.ext import commands

log = getLogger(__name__)


class Cog(commands.Cog):
    """ The Cog base class that all cogs should inherit from. """

    def __init__(self, bot: "Bot"):
        self.bot: "Bot" = bot


class BoolConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str):
        if argument[0].lower() == "f":
            return False
        elif argument[0].lower() == "t":
            return True
        else:
            raise commands.BadArgument(f'can not convert {argument} to True or False')


async def get_text(session: aiohttp.ClientSession, url: str) -> str:
    log.debug(f"fetched url: {url}")
    async with session.get(url) as content:
        return await content.text()


async def get_json(session: aiohttp.ClientSession, url: str, body=None) -> dict:
    log.debug(f"fetched json: {url}, body: {body}")
    async with session.get(url, data=body) as content:
        return await content.json()


async def get_xml(session: aiohttp.ClientSession, url: str) -> dict:
    log.debug(f"fetched xml: {url}")
    async with session.get(url) as content:
        return xmltodict.parse(await content.text())


def metar_only_in_vasa(ctx: commands.Context):
    try:
        return not (ctx.guild.id == 377567755743789064 and ctx.command.name not in ['help', 'invite', 'info', 'metar'])
    except AttributeError:
        return True


def timing(log=None):
    """
    a decorator to log how long a function takes to execute.
    """
    if log is None:
        prt = print
    else:
        prt = log.debug

    def inner_function(function: Callable):
        """
        a decorator to log how long a function takes to execute.
        """

        @wraps(function)
        def wrapper(*args, **kwargs):
            prt(f"starting {function.__name__}..")
            ts = time.time()
            result = function(*args, **kwargs)
            te = time.time()
            prt(f"{function.__name__} completed, took {te - ts} seconds")
            return result

        return wrapper

    return inner_function
