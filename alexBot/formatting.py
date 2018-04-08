# -*- coding: utf-8 -*-

"""
MIT License

Copyright (c) 2017 - 2018 FrostLuma

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import asyncio
import re

import discord


# todo
__all__ = (
    'transform_mentions', 'clean_formatting', 'clean_codeblock', 'clean_accents', 'clean_text', 'Table',
)


NUMERIC_RE = re.compile(r'^([\d.]+)$')
FORMATTING_RE = re.compile(r'(<?https?://\S*|[*_~`\\])')
MENTION_RE = re.compile(r'<@!?&?#?(\d{15,21})>|(@everyone|@here)')


def transform_mentions(text, guild):
    """
    Replaces all mentions inside a string with the associated names.

    Parameters
    ----------
    text : str
        The text to transform.
    guild : discord.Guild
        The Guild the text will be sent in. Used to find names of roles, users, and channels.

    Returns
    -------
    str
        The cleaned up text.
    """

    def replace(match):
        mention = match.group()

        if '<@&' in mention:
            role_id = int(match.groups()[0])
            role = discord.utils.get(guild.roles, id=role_id)

            if role is not None:
                mention = f'@{role.name}'
        elif '<@' in mention:
            user_id = int(match.groups()[0])
            member = guild.get_member(user_id)

            if member is not None:
                mention = f'@{member.name}'
        elif '<#' in mention:
            channel_id = int(match.groups()[0])
            channel = guild.get_member(channel_id)

            if channel is not None:
                mention = f'@{channel}'

        if mention in ('@everyone', '@here'):
            mention = mention.replace('@', '@\N{ZERO WIDTH SPACE}')

        return mention

    return MENTION_RE.sub(replace, text)


def clean_formatting(text):
    """Escapes markdown, codeblocks and escaped links from text."""

    transforms = {
        '*': '\*',
        '_': '\_',
        '~': '\~',
        '`': '\`',
        '\\': '\\\\',
    }

    def replace(match):
        group = match.group()

        try:
            return transforms[group]
        except KeyError:
            return f'\<{group}>' if '<' in group else f'<{group}>'

    return FORMATTING_RE.sub(replace, text)


def clean_codeblock(text):
    """
    Removes codeblocks (grave accents) and syntax highlight indicators from a text if present.

    .. note:: only the start and end of a string is checked, the text is allowed to have grave accents in the middle
    """

    if text.startswith('```') and text.endswith('```'):
        text = text[3:-3]

        first_line = text.split('\n')[0:1][0]

        # if the first line is a single word it's likely a syntax highlight indicator like py, sql, etc
        if len(first_line.split()) == 1:

            # cut off the first line as this removes the highlight indicator regardless of length
            text = '\n'.join(text.split('\n')[1:])

    elif text.startswith('`') and text.endswith('`'):
        text = text[1:-1]

    return text.strip()


def clean_accents(text):
    """Replaces all grave accents with modifier grave accents to allow using text in codeblocks."""
    return text.replace('\N{GRAVE ACCENT}', '\N{MODIFIER LETTER GRAVE ACCENT}')


def clean_text(text, guild):
    """Utility method to clean text as often multiple methods get used."""

    text = clean_formatting(text)
    return transform_mentions(text, guild)


class Table:
    def __init__(self, *titles):
        header_row = [str(x) for x in titles]

        self._rows = [header_row]
        self._right_widths = [len(x) for x in header_row]
        self._left_widths = [0 for _ in range(len(header_row))]

    def _update_widths(self, row):
        for idx, entry in enumerate(row):
            length = len(entry)
            is_numeric = NUMERIC_RE.match(entry) is not None

            if is_numeric:
                center = entry.find('.')

                if center + 1 > self._left_widths[idx]:
                    self._left_widths[idx] = center + 1

                remaining = length - center - 1

                if remaining > self._right_widths[idx]:
                    self._right_widths[idx] = remaining

            elif length > self._right_widths[idx]:
                self._right_widths[idx] = length

    def add_row(self, *row):
        """
        Add a row to the table.

        .. note :: There's no check for the number of items entered, this may cause issues rendering if not correct.
        """

        row = [str(x) for x in row]

        self._rows.append(row)
        self._update_widths(row)

    def _render(self):
        widths = [self._left_widths[idx] + self._right_widths[idx] for idx in range(len(self._rows[0]))]

        # column title is centered in the middle of each field
        title_row = '|'.join(f' {field:^{widths[idx]}} ' for idx, field in enumerate(self._rows[0]))
        separator_row = '+'.join('-' * (widths[idx] + 2) for idx in range(len(self._rows[0])))

        drawn = [title_row, separator_row]

        for row in self._rows[1:]:
            drawn.append(self._render_row(row))

        return '\n'.join(drawn)

    def _render_row(self, row):
        columns = []

        for idx, entry in enumerate(row):
            if self._left_widths[idx] != 0:
                if entry.find('.') == -1:
                    columns.append(f' {entry:>{self._right_widths[idx]}} ')
                else:
                    left, *right = entry.split('.')

                    # if we're dealing with eg. version numbers like 1.12.1 this will be a list
                    # we're aligning the number on the major release to make it look acceptable
                    if not isinstance(right, str):
                        right = '.'.join(right)

                    columns.append(f' {left:>{self._left_widths[idx] - 1}}.{right:<{self._right_widths[idx]}} ')

                continue

            # make sure the codeblock this will end up in won't get escaped
            entry = entry.replace('`', '\u200b`')

            # regular text gets aligned to the left
            columns.append(f' {entry:<{self._right_widths[idx]}} ')

        return '|'.join(columns)

    async def render(self, loop=None):
        """Returns a rendered version of the table."""
        loop = loop or asyncio.get_event_loop()

        return await loop.run_in_executor(None, self._render)
