import asyncio
import logging
import math
import os
import re
import shutil
import subprocess
from functools import partial

import discord
from discord.errors import DiscordException
from discord.ext import commands
from slugify import slugify
from youtube_dl import DownloadError, YoutubeDL

from ..tools import Cog, is_in_channel, is_in_guild, timing

log = logging.getLogger(__name__)

REGEXES = [
    re.compile(r'https?://vm\.tiktok\.com/[a-zA-Z0-9#-_!*\(\),]{6,}/'),
    re.compile(r'https?://(?:w{3}\.)tiktok.com/@.*/video/\d{18,20}\??[a-zA-Z0-9#-_!*\(\),]*'),
    re.compile(r'https?://(?:v\.)?redd\.it/[a-zA-Z0-9#-_!*\(\),]{6,}'),
    re.compile(r'https?://(?:\w{,32}\.)?reddit\.com\/(?:r\/\w+\/)?comments\/[a-zA-Z0-9#-_!*\(\),]{6,}'),
    re.compile(r'https?://twitter.com\/[a-zA-Z0-9#-_!*\(\),]{0,20}/status/\d{0,25}\??[a-zA-Z0-9#-_!*\(\),]*'),
]

TARGET_SHRINK_SIZE = (8 * 10 ** 6 - 128 * 1000) * 8  # 8 MB - 128 KB in bits
MAX_VIDEO_LENGTH = 5 * 60  # 5 Minutes
AUDIO_BITRATE = 64 * 1000  # 64 Kbits
BUFFER_CONSTANT = 20  # Magic number, see https://unix.stackexchange.com/a/598360

FFPROBE_CMD = 'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 in.mp4'
FFMPEG_CMD = 'ffmpeg -i in.mp4 -y -b:v {0} -maxrate:v {0} -b:a {1} -maxrate:a {1} -bufsize:v {2} {3}.mp4'


class NotAVideo(Exception):
    pass


class Video_DL(Cog):
    active = False
    encode_lock = asyncio.Lock()
    mirror_upload_lock = asyncio.Lock()

    @staticmethod
    def download_video(url, id):
        ytdl = YoutubeDL({'outtmpl': f'{id}.mp4'})
        try:
            data = ytdl.extract_info(url, download=True)
        except DownloadError:
            raise NotAVideo(False)
        try:
            if data['ext'] not in ['mp4', 'gif', 'm4a', 'mov']:
                raise NotAVideo(data['url'])
        except KeyError:
            pass
        return REGEXES[3].sub('', data['title'])

    @staticmethod
    def download_audio(url, id):
        ydl_opts = {
            'outtmpl': f'{id}.%(ext)s',
            'format': 'bestaudio/best',
            'postprocessors': [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'm4a',
                    'preferredquality': '64',
                }
            ],
        }
        ytdl = YoutubeDL(ydl_opts)
        data = ytdl.extract_info(url, download=True)
        try:
            return data['title']
        except KeyError:
            return "audio"

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        loop = asyncio.get_running_loop()
        if message.guild is None or message.author == self.bot.user:
            return
        if not (await self.bot.db.get_guild_data(message.guild.id)).config.tikTok:
            return

        matches = None

        for regex in REGEXES:
            matches = regex.match(message.content)
            if matches:
                break

        if matches is None:
            return

        match = matches.group(0)
        log.info(f'collecting {match} for {message.author}')
        async with message.channel.typing():
            try:

                if match:
                    await message.channel.trigger_typing()
                    try:
                        await message.add_reaction('📥')
                    except discord.Forbidden:
                        pass

                    task = partial(self.download_video, match, message.id)
                    try:
                        title = await self.bot.loop.run_in_executor(None, task)
                    except NotAVideo as e:
                        if e.args[0]:
                            await message.reply(e, mention_author=False)
                            try:
                                await message.add_reaction('✅')
                            except DiscordException:
                                pass
                        return
                    loop.create_task(message.remove_reaction('📥', self.bot.user))

                    if os.path.getsize(f'{message.id}.mp4') > 8000000:
                        loop.create_task(message.add_reaction('🪄'))  # magic wand

                        async with self.encode_lock:
                            task = partial(self.transcode_shrink, message.id)
                            await self.bot.loop.run_in_executor(None, task)

                    # file is MESSAGE.ID.mp4, need to create discord.File and upload it to channel then delete out.mp4
                    file = discord.File(f'{message.id}.mp4', 'vid.mp4')
                    loop.create_task(message.add_reaction('📤'))
                    await message.reply(title, file=file, mention_author=False)
                    loop.create_task(message.remove_reaction('📤', self.bot.user))
                    try:
                        await message.add_reaction('✅')
                    except DiscordException:
                        pass

            except Exception as e:
                log.warn(f'Exception occurred processing video {e}')

                try:
                    await message.add_reaction('❌')
                except discord.Forbidden:
                    await message.channel.send('Something broke')

            finally:
                await message.remove_reaction('📥', self.bot.user)

                if os.path.exists(f'{message.id}.mp4'):
                    os.remove(f'{message.id}.mp4')

    @staticmethod
    @timing(log=log)
    def transcode_shrink(id):
        shutil.copyfile(f'{id}.mp4', 'in.mp4')
        os.remove(f'{id}.mp4')

        try:
            video_length = float(subprocess.check_output(FFPROBE_CMD.split(' ')).decode("utf-8"))

            if video_length > MAX_VIDEO_LENGTH:
                raise commands.CommandInvokeError('Video is too large.')

            target_total_bitrate = TARGET_SHRINK_SIZE / video_length
            buffer_size = math.floor(TARGET_SHRINK_SIZE / BUFFER_CONSTANT)
            target_video_bitrate = target_total_bitrate - AUDIO_BITRATE

            command_formatted = FFMPEG_CMD.format(
                str(target_video_bitrate), str(AUDIO_BITRATE), str(buffer_size), str(id)
            )

            subprocess.check_call(command_formatted.split(' '))

        except Exception as e:
            log.warn(f'Exception occurred transcoding video {e}')

        finally:
            if os.path.exists('in.mp4'):
                os.remove('in.mp4')

    @commands.command()
    @is_in_guild(791528974442299412)
    @is_in_channel(791530687102451712)
    async def mirror(self, ctx: commands.Context, url: str):
        """Mirrors a youtube-dl compatible URL to a discord file upload.
        also connects to your voice channel, requests the bot play the song, and leaves."""
        async with self.mirror_upload_lock:
            async with ctx.typing():
                try:
                    task = partial(self.download_audio, url, ctx.message.id)
                    title = await self.bot.loop.run_in_executor(None, task)

                    try:
                        msg = await ctx.send(
                            file=discord.File(f"{ctx.message.id}.m4a", filename=f'{slugify(title)}.m4a')
                        )
                    except discord.errors.HTTPException:
                        return await ctx.send("file too large :(")
                    voice_connection = await ctx.author.voice.channel.connect()
                    await ctx.send(f"!play {msg.attachments[0].url}")
                    await voice_connection.disconnect()
                finally:
                    if os.path.exists(f"{ctx.message.id}.m4a"):
                        os.remove(f"{ctx.message.id}.m4a")


def setup(bot):
    bot.add_cog(Video_DL(bot))
