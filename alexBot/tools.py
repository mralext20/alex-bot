import datetime
import functools
import math
import posixpath
import time
from functools import wraps
from typing import TYPE_CHECKING, Callable, Generator, Iterable, Sequence, Tuple, TypeVar, Union
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


def convert_to_bool(argument: str) -> bool:
    lowered = argument.lower()
    if lowered in ('yes', 'y', 'true', 't', '1', 'enable', 'on'):
        return True
    elif lowered in ('no', 'n', 'false', 'f', '0', 'disable', 'off'):
        return False
    else:
        raise commands.BadBoolArgument(lowered)


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


def grouper(iterable: Sequence[_T], n: int) -> Generator[Sequence[_T], None, None]:
    """
    given a iterable, yield that iterable back in chunks of size n. last item will be any size.
    """
    for i in range(math.ceil(len(iterable) / n)):
        yield iterable[i * n : i * n + n]


def time_cache(max_age: int, maxsize=128, typed=False):
    """Least-recently-used cache decorator with time-based cache invalidation.

    Args:
        max_age: Time to live for cached results (in seconds).
        maxsize: Maximum cache size (see `functools.lru_cache`).
        typed: Cache on distinct input types (see `functools.lru_cache`).

    copied from stackoverflow: https://stackoverflow.com/a/63674816
    """

    def _decorator(fn):
        @functools.lru_cache(maxsize=maxsize, typed=typed)
        def _new(*args, __time_salt, **kwargs):
            return fn(*args, **kwargs)

        @functools.wraps(fn)
        def _wrapped(*args, **kwargs):
            return _new(*args, **kwargs, __time_salt=int(time.time() / max_age))

        return _wrapped

    return _decorator


timeUnits = {
    's': lambda v: v,
    'm': lambda v: v * 60,
    'h': lambda v: v * 60 * 60,
    'd': lambda v: v * 60 * 60 * 24,
    'w': lambda v: v * 60 * 60 * 24 * 7,
    'M': lambda v: v * 60 * 60 * 24 * 30,
}


def resolve_duration(data: str, tz: datetime.tzinfo = timezone('UTC')) -> datetime.timedelta:
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

    return datetime.timedelta(seconds=value)
