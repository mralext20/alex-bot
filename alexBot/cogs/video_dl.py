import asyncio
import io
import json
import logging
import math
import os
import re
import shutil
import subprocess
import traceback
from functools import partial
from typing import List, Optional, Tuple

import aiohttp
import discord
import httpx
from discord.errors import DiscordException
from discord.ext import commands
from slugify import slugify
from sqlalchemy import select
from yt_dlp import DownloadError, YoutubeDL

from alexBot import database as db
from alexBot import tools
from alexBot.cobalt import Cobalt, RequestBody

from ..tools import Cog, grouper, is_in_guild, timing

log = logging.getLogger(__name__)


DOMAINS = [
    "x.com",
    "twitter.com",
    "tiktok.com",
    "instagram.com",
    "facebook.com",
    "youtube.com",
    "youtu.be",
    "vimeo.com",
]

MAX_VIDEO_LENGTH = 5 * 60  # 5 Minutes
AUDIO_BITRATE = 64 * 1000  # 64 Kbits
BUFFER_CONSTANT = 20  # Magic number, see https://unix.stackexchange.com/a/598360

FFPROBE_CMD = 'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 pipe:'
FFMPEG_CMD = 'ffmpeg -i pipe: -y -b:v {0} -maxrate:v {0} -b:a {1} -maxrate:a {1} -bufsize:v {2} pipe:'


class NotAVideo(Exception):
    pass


class Video_DL(Cog):
    encode_lock = asyncio.Lock()
    mirror_upload_lock = asyncio.Lock()

    @Cog.listener()
    async def on_message(self, message: discord.Message, override=False, new_deleter=None):
        loop = asyncio.get_running_loop()
        if message.guild is None or (message.author == self.bot.user and not override):
            return
        gc = None
        async with db.async_session() as session:
            gc = await session.scalar(select(db.GuildConfig).where(db.GuildConfig.guildId == message.guild.id))
            if not gc:
                # create one
                gc = db.GuildConfig(guildId=message.guild.id)
                session.add(gc)
                await session.commit()
        if not gc.tikTok:
            return

        # find the link to the video (first only)
        match = None
        for domain in DOMAINS:
            if match := re.search(rf'(https?://[^ ]*{domain}/[^ ]*)', message.content):
                break

        if not match:
            return

        async with message.channel.typing():
            stuff = None

            cobalt = Cobalt()
            rq = RequestBody(url=match.group(1))
            res = await cobalt.process(rq)
            async with aiohttp.ClientSession() as session:
                match res.status:
                    case "stream" | "redirect":
                        # download the stream to reupload to discord
                        async with session.get(res.url) as response:
                            stuff = await response.read()
                            if not response.content_disposition:
                                raise NotAVideo("No content disposition found.")
                            bytes = io.BytesIO(stuff)
                            if len(bytes.getvalue()) > message.guild.filesize_limit:
                                bytes = self.transcode_shrink(bytes, message.guild.filesize_limit)
                            uploaded = await message.channel.send(
                                file=discord.File(io.BytesIO(stuff), filename=response.content_disposition.filename)
                            )
                    case "picker":
                        # gotta download the photos to post, batch by 10's
                        if not res.picker:
                            raise NotAVideo("No pickers found.")
                        images = await asyncio.gather(*[session.get(each.url) for each in res.picker])
                        attachments: List[discord.File] = []
                        for image in images:
                            stuff = await image.read()
                            if not image.content_disposition:
                                raise NotAVideo("No content disposition found.")

                            attachments.append(
                                discord.File(io.BytesIO(stuff), filename=image.content_disposition.filename)
                            )
                        uploaded = await message.channel.send(files=attachments)
                    case "error":
                        log.error(f"Error in cobalt with url {rq.url}: {res.text}")

        if uploaded:
            try:
                await uploaded.add_reaction("🗑️")
            except DiscordException:
                return
            try:
                await message.edit(suppress=True)
            except DiscordException:
                pass

            def check(reaction: discord.Reaction, user: discord.User):
                return (
                    reaction.emoji == "🗑️"
                    and user.id in [message.author.id, new_deleter]
                    and reaction.message.id == uploaded.id
                )

            try:
                await self.bot.wait_for('reaction_add', timeout=60 * 5, check=check)
            except asyncio.TimeoutError:
                await uploaded.remove_reaction("🗑️", self.bot.user)
            else:
                # if we are here, someone with the power to do so want's to delete the upload
                await uploaded.delete()

    @staticmethod
    @timing(log=log)
    def transcode_shrink(content: io.BytesIO, limit: float) -> io.BytesIO:
        shutil.copyfile(f'{id}.mp4', 'in.mp4')
        os.remove(f'{id}.mp4')
        limit = limit * 8
        try:
            video_length = math.ceil(
                float(subprocess.check_output(FFPROBE_CMD.split(' '), stdin=content).decode("utf-8"))
            )
            content.seek(0)  # reset data
            if video_length > MAX_VIDEO_LENGTH:
                raise commands.CommandInvokeError('Video is too large.')

            target_total_bitrate = limit / video_length
            buffer_size = math.floor(limit / BUFFER_CONSTANT)
            target_video_bitrate = target_total_bitrate - AUDIO_BITRATE

            command_formatted = FFMPEG_CMD.format(str(target_video_bitrate), str(AUDIO_BITRATE), str(buffer_size))
            output = io.BytesIO()
            subprocess.check_call(command_formatted.split(' '), stdin=content, stdout=output)
            output.seek(0)
            return output
        except Exception as e:
            raise Exception('Exception occurred transcoding video', traceback.format_exc())


async def setup(bot):
    await bot.add_cog(Video_DL(bot))
