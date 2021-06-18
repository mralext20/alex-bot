import math
import posixpath
import time
from functools import wraps
from typing import TYPE_CHECKING, Callable, Generator, Iterable, TypeVar
from urllib.parse import urlparse

if TYPE_CHECKING:
    from bot import Bot

import re
from logging import getLogger

import aiohttp
import discord
import xmltodict
from discord.ext import commands
from discord.ext.commands.converter import IDConverter

log = getLogger(__name__)

_T = TypeVar("_T")


class Cog(commands.Cog):
    """The Cog base class that all cogs should inherit from."""

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


async def get_json(session: aiohttp.ClientSession, url: str) -> dict:
    log.debug(f"fetched json: {url}")
    async with session.get(url) as content:
        return await content.json()


async def get_xml(session: aiohttp.ClientSession, url: str) -> dict:
    log.debug(f"fetched xml: {url}")
    async with session.get(url) as content:
        return xmltodict.parse(await content.text())


def metar_only_in_vasa(ctx: commands.Context):
    try:
        return not (
            ctx.guild.id == 377567755743789064
            and ctx.command.name
            not in [
                'help',
                'invite',
                'info',
                'metar',
                'taf',
                'jsk',
            ]
        )
    except AttributeError:
        return True


def is_in_guild(guild_id):
    async def predicate(ctx):
        return ctx.guild and ctx.guild.id == guild_id

    return commands.check(predicate)


def is_in_channel(channel_id):
    async def predicate(ctx):
        return ctx.channel and ctx.channel.id == channel_id

    return commands.check(predicate)


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


def grouper(iterable: Iterable[_T], n: int) -> Generator[Iterable[_T], None, None]:
    """
    given a iterable, yield that iterable back in chunks of size n. last item will be any size.
    """
    for i in range(math.ceil(len(iterable) / n)):
        yield iterable[i * n : i * n + n]


def transform_neosdb(url: str) -> str:
    url = urlparse(url)
    return f"https://cloudxstorage.blob.core.windows.net/assets{posixpath.splitext(url.path)[0]}"


class ObjectConverter(IDConverter):
    """Converts to a :class:`~discord.Object`.
    The argument must follow the valid ID or mention formats (e.g. `<@80088516616269824>`).


    The lookup strategy is as follows (in order):
    1. Lookup by ID.
    2. Lookup by member, role, or channel mention.
    """

    async def convert(self, ctx: commands.Context, argument: str) -> discord.Object:
        match = self._get_id_match(argument) or re.match(r'<(?:@(?:!|&)?|#)([0-9]{15,20})>$', argument)

        if match is None:
            raise commands.errors.BadArgument(f"{argument} does not follow a valid ID or mention format.")
        result = int(match.group(1))

        return discord.Object(id=result)
