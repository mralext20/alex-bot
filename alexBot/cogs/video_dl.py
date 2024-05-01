import asyncio
import io
import logging
import math
import os
import re
import subprocess
import traceback
from functools import partial
from typing import List

import aiohttp
import discord
from discord.errors import DiscordException
from discord.ext import commands
from slugify import slugify
from sqlalchemy import select

from alexBot import database as db
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
    "reddit.com",
]

MAX_VIDEO_LENGTH = 5 * 60  # 5 Minutes
AUDIO_BITRATE = 64 * 1000  # 64 Kbits
BUFFER_CONSTANT = 20  # Magic number, see https://unix.stackexchange.com/a/598360

FFPROBE_CMD = 'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 in.mp4'
FFMPEG_CMD = 'ffmpeg -i in.mp4 -y -b:v {0} -maxrate:v {0} -b:a {1} -maxrate:a {1} -bufsize:v {2} out.mp4'


#  -loglevel 8
class NotAVideo(Exception):
    pass


class Video_DL(Cog):
    encode_lock = asyncio.Lock()
    mirror_upload_lock = asyncio.Lock()

    @Cog.listener()
    async def on_message(self, message: discord.Message, override=False, new_deleter=None):
        log.debug("on_message function started")
        if message.guild is None or (message.author == self.bot.user and not override):
            log.debug("Message is from a guild or from the bot user. Returning without processing.")
            return
        gc = None
        async with db.async_session() as session:
            log.debug("Starting DB session")
            gc = await session.scalar(select(db.GuildConfig).where(db.GuildConfig.guildId == message.guild.id))
            if not gc:
                # create one
                log.debug("GuildConfig not found. Creating a new one.")
                gc = db.GuildConfig(guildId=message.guild.id)
                session.add(gc)
                await session.commit()
        if not gc.tikTok:
            log.debug("tikTok is not enabled for this guild. Returning without processing.")
            return

        # find the link to the video (first only)
        match = None
        for domain in DOMAINS:
            log.debug(f"Searching for domain: {domain} in message content")
            if match := re.search(rf'(https?://[^ ]*{domain}/[^ ]*)', message.content):
                if domain in ["youtube.com", "youtu.be"]:
                    if 'shorts' in match.group(1) or 'clip' in match.group(1):
                        log.debug("Match found for youtube SHORTS / CLIPS domain. Breaking loop.")
                        break
                else:
                    log.debug(f"Match found for domain: {domain}. Breaking loop.")
                    break

        if not match:
            log.debug("No matching domain found in message content. Returning without processing.")
            return

        async with message.channel.typing():
            log.debug("Typing indicator started")
            stuff = None

            cobalt = Cobalt()
            rq = RequestBody(url=match.group(1))
            res = await cobalt.process(rq)
            async with aiohttp.ClientSession(headers=cobalt.HEADERS) as session:
                match res.status:
                    case "stream" | "redirect":
                        # download the stream to reupload to discord
                        log.debug("Status is stream or redirect. Downloading the stream.")
                        async with session.get(res.url) as response:
                            stuff = await response.read()
                            if not response.content_disposition:
                                raise NotAVideo("No content disposition found.")
                            bytes = io.BytesIO(stuff)
                            if len(bytes.getvalue()) > message.guild.filesize_limit:
                                async with self.encode_lock:
                                    task = partial(self.transcode_shrink, bytes, message.guild.filesize_limit)
                                    bytes = await self.bot.loop.run_in_executor(None, task)
                                filename = response.content_disposition.filename.split(".")[0] + ".mp4"
                            else:
                                filename = response.content_disposition.filename
                            uploaded = await message.reply(
                                mention_author=False,
                                content=filename.split('.')[0],
                                file=discord.File(bytes, filename=filename),
                            )
                    case "picker":
                        # gotta download the photos to post, batch by 10's
                        log.debug("Status is picker. Downloading the photos.")
                        if not res.picker:
                            raise NotAVideo("No pickers found.")
                        images = await asyncio.gather(*[session.get(each.url) for each in res.picker])
                        attachments: List[discord.File] = []
                        for m, group in enumerate(grouper(images, 10)):
                            for n, image in enumerate(group):
                                stuff = await image.read()
                                if not image.content_disposition:
                                    filename = f"{n+(m*10)}.{image.url.suffix}"
                                else:
                                    filename = image.content_disposition.filename
                                attachments.append(discord.File(io.BytesIO(stuff), filename=filename))
                            uploaded = await message.reply(mention_author=False, files=attachments)
                    case "error":
                        log.error(f"Error in cobalt with url {rq.url}: {res.text}")
        log.debug("on_message function ended")

        if uploaded:
            try:
                await uploaded.add_reaction("🗑️")
            except DiscordException:
                return
            # try:
            #     await message.edit(suppress=True)
            # except DiscordException:
            #     pass

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
        limit = limit * 8
        try:
            with open("in.mp4", "wb") as f:
                f.write(content.getvalue())
            fprobe = subprocess.Popen(FFPROBE_CMD.split(' '), stdout=subprocess.PIPE)
            fprobe.wait()
            video_length = math.ceil(float(fprobe.communicate()[0].decode("utf-8")))
            content.seek(0)  # reset data
            if video_length > MAX_VIDEO_LENGTH:
                raise commands.CommandInvokeError('Video is too large.')

            target_total_bitrate = limit / video_length
            buffer_size = math.floor(limit / BUFFER_CONSTANT)
            target_video_bitrate = target_total_bitrate - AUDIO_BITRATE

            command_formatted = FFMPEG_CMD.format(str(target_video_bitrate), str(AUDIO_BITRATE), str(buffer_size))
            log.debug(f"Transcoding video with command: {command_formatted}")
            ffmpeg = subprocess.Popen(command_formatted.split(' '))

            ffmpeg.communicate()[0]
            ffmpeg.wait()
            with open("out.mp4", "rb") as f:
                return io.BytesIO(f.read())
        except Exception as e:
            raise Exception('Exception occurred transcoding video', traceback.format_exc())
        finally:
            try:
                os.remove("out.mp4")
            except Exception:
                pass


async def setup(bot):
    await bot.add_cog(Video_DL(bot))
