# -*- coding: utf-8 -*-
import asyncio
import contextlib
import logging
import time

import discord
from discord.ext import commands


DEFAULT_SILENCED = ['discord', 'websockets']


@contextlib.contextmanager
def setup_logging(level=logging.DEBUG, *, webhooks=None, silenced=None):
    """
    Context manager which sets up logging to stdout at DEBUG level and optionally Discord webhooks at different levels.

    Parameters
    ----------
    level : int
        The logging level the root logger is set to. Defaults to 10 (logging.DEBUG)
    webhooks : Dict[int, discord.Webhook]
        A dictionary of logging levels and Discord webhooks which will be added as handlers.
    silenced : List[str]
        Loggers which are only set to level 20 (logging.INFO). Defaults to ['discord', 'websockets']
    """
    try:
        log = logging.getLogger()
        log.setLevel(level)

        if silenced is None:
            silenced = DEFAULT_SILENCED

        for name in silenced:
            logger = logging.getLogger(name)
            logger.setLevel(logging.INFO)

        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
        )

        def add_handler(handler):
            handler.setFormatter(formatter)
            log.addHandler(handler)

        add_handler(logging.StreamHandler())

        if webhooks is not None:
            for level, webhook in webhooks.items():
                add_handler(DiscordHandler(webhook, level=level))

        yield
    finally:
        logging.shutdown()


class DiscordHandler(logging.Handler):
    """
    A custom logging handler which sends records to a Discord webhook.

    Messages are queued internally and only sent every 5 seconds to avoid waiting due to ratelimits.

    Parameters
    ----------
    webhook : discord.Webhook
        The webhook the logs will be sent to
    level : Optional[int]
        The level this logger logs at
    loop : Optional[asyncio.AbstractEventLoop]
        The loop which the handler will run on

    Attributes
    ----------
    closed : bool
        Whether this handler is closed or not
    """

    def __init__(self, webhook: discord.Webhook, *, level=None, loop=None):
        super().__init__(level)

        self.webhook = webhook
        self.loop = loop = loop or asyncio.get_event_loop()

        self.closed = False

        self._buffer = []

        self._last_emit = 0
        self._can_emit = asyncio.Event()

        self._emit_task = loop.create_task(self.emitter())

    def emit(self, record: logging.LogRecord):
        if record.levelno != self.level:
            return  # only log the handlers level to the handlers channel, not above (unlike a normal handler)

        msg = self.format(record).replace('\N{GRAVE ACCENT}', '\N{MODIFIER LETTER GRAVE ACCENT}')

        if record.levelno == logging.ERROR:
            chunks = (msg[x:x + 1987] for x in range(0, len(msg), 1987))

            paginator = commands.Paginator(prefix='```py\n', suffix='```')
            for chunk in chunks:
                paginator.add_line(chunk)

            for page in paginator.pages:
                self._buffer.append(page)
        else:
            for chunk in (msg[x:x+1996] for x in range(0, len(msg), 1996)):
                # not using the paginators prefix/suffix due to this resulting in weird indentation on newlines
                self._buffer.append(f'`{chunk}`')

        self._can_emit.set()

    async def emitter(self):
        while not self.closed:
            now = time.monotonic()

            send_delta = now - self._last_emit
            if send_delta < 5:
                await asyncio.sleep(5 - send_delta)

            self._last_emit = now

            paginator = commands.Paginator(prefix='', suffix='')

            for message in self._buffer:
                paginator.add_line(message)

            self._buffer.clear()
            self._can_emit.clear()

            for page in paginator.pages:
                await self.webhook.execute(page)

            await self._can_emit.wait()

    def close(self):
        try:
            self.closed = True
            self._emit_task.cancel()
        finally:
            super().close()
