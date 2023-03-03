import datetime
import math
import posixpath
import time
from functools import wraps
from typing import TYPE_CHECKING, Callable, Generator, Iterable, Tuple, TypeVar, Union
from urllib.parse import urlparse

import discord
from jishaku.paginators import PaginatorInterface
from pytz import timezone

if TYPE_CHECKING:
    from bot import Bot

from logging import getLogger

import aiohttp
import xmltodict
from discord.ext import commands

log = getLogger(__name__)

_T = TypeVar("_T")


class InteractionPaginator(PaginatorInterface):
    # send_interaction takes an interaction and uses that to send the paginator
    async def send_interaction(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            **self.send_kwargs,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        self.message = await interaction.original_response()
        self.send_lock.set()
        if self.task:
            self.task.cancel()

        self.task = self.bot.loop.create_task(self.wait_loop())

        return self


class Cog(commands.Cog):
    """The Cog base class that all cogs should inherit from."""

    def __init__(self, bot: "Bot"):
        self.bot: "Bot" = bot


async def get_text(session: aiohttp.ClientSession, url: str) -> str:
    log.debug(f"fetched url: {url}")
    async with session.get(url) as content:
        return await content.text()


async def get_json(session: aiohttp.ClientSession, url: str, **kwargs) -> dict:
    log.debug(f"fetched json: {url}")
    async with session.get(url, **kwargs) as content:
        return await content.json()


async def get_xml(session: aiohttp.ClientSession, url: str) -> dict:
    log.debug(f"fetched xml: {url}")
    async with session.get(url) as content:
        return xmltodict.parse(await content.text())


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


timeUnits = {
    's': lambda v: v,
    'm': lambda v: v * 60,
    'h': lambda v: v * 60 * 60,
    'd': lambda v: v * 60 * 60 * 24,
    'w': lambda v: v * 60 * 60 * 24 * 7,
}


def resolve_duration(data) -> datetime.datetime:
    """
    Takes a raw input string formatted 1w1d1h1m1s (any order)
    and converts to timedelta
    Credit https://github.com/b1naryth1ef/rowboat via MIT license
    data: str
    """
    value = 0
    digits = ''

    for char in data:
        if char.isdigit():
            digits += char
            continue

        if char not in timeUnits or not digits:
            raise KeyError('Time format not a valid entry')

        value += timeUnits[char](int(digits))
        digits = ''

    return datetime.datetime.now(tz=timezone('UTC')) + datetime.timedelta(seconds=value + 1)
