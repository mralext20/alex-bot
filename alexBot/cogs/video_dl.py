import asyncio
import logging
import math
import os
import re
import shutil
import subprocess
from functools import partial

import discord
import httpx
from discord.errors import DiscordException
from discord.ext import commands
from slugify import slugify
from youtube_dlc import DownloadError, YoutubeDL

from ..tools import Cog, is_in_channel, is_in_guild, timing

log = logging.getLogger(__name__)
REDDIT_REGEX = re.compile(r'https?://(?:\w{2,32}\.)?reddit\.com/(?:r\/\w+\/)?(?:comments|gallery)\/[\w]+\/?\w*')
REGEXES = [
    re.compile(r'DISABLEDhttps?://vm\.tiktok\.com/[a-zA-Z0-9#-_!*\(\),]{6,}/'),
    re.compile(r'DISABLEDhttps?://(?:w{3}\.)tiktok.com/@.*/video/\d{18,20}\??[a-zA-Z0-9#-_!*\(\),]*'),
    re.compile(r'https?://(?:v\.)?redd\.it/[a-zA-Z0-9#-_!*\(\),]{6,}'),
    re.compile(r'https?://twitter\.com\/[a-zA-Z0-9#-_!*\(\),]{0,20}/status/\d{0,25}\??[a-zA-Z0-9#-_!*\(\),]*'),
    re.compile(r'https?://t\.co\/[a-zA-Z0-9#-_!*\(\),]{0,10}'),
    re.compile(r'https?://(?:www\.)instagram\.com/(?:p|reel)/[a-zA-Z0-9-_]{11}/'),
    re.compile(r'https?:\/\/clips.twitch.tv\/[a-zA-Z0-9-]{0,64}'),
]

MAX_VIDEO_LENGTH = 5 * 60  # 5 Minutes
AUDIO_BITRATE = 64 * 1000  # 64 Kbits
BUFFER_CONSTANT = 20  # Magic number, see https://unix.stackexchange.com/a/598360

FFPROBE_CMD = 'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 in.mp4'
FFMPEG_CMD = 'ffmpeg -i in.mp4 -y -b:v {0} -maxrate:v {0} -b:a {1} -maxrate:a {1} -bufsize:v {2} {3}.mp4'


class NotAVideo(Exception):
    pass


class Video_DL(Cog):
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
        return REGEXES[5].sub(
            '', f"{data['title']} - {data['description']}" if data.get('description') else data['title']
        )

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

    async def convert_reddit(self, message: discord.Message):
        matches = REDDIT_REGEX.match(message.content)
        if matches:
            async with httpx.AsyncClient() as session:
                resp = await session.get(url=matches.group(0) + '.json', headers={'User-Agent': 'AlexBot:v1.0.0'})
                data = resp.json()[0]['data']['children'][0]['data']
                # handle gallery
                if 'gallery_data' in data:
                    images = [item for item in data['gallery_data']['items']]
                    counter = 0
                    resp_text = ''
                    for image in images:
                        image_type = data['media_metadata'][image['media_id']]['m'].split('/')[1]
                        if counter == 5:
                            counter = 0
                            await message.reply(resp_text)
                            resp_text = ''
                        resp_text += f'https://i.redd.it/{image["media_id"]}.{image_type}'
                        if caption := image.get('caption'):
                            resp_text += f' ; {caption}'
                        if link := image.get('outbound_url'):
                            resp_text += f' ; <{link}>'

                        resp_text += '\n'
                        counter += 1
                    await message.reply(resp_text)
                # handle videos
                elif data['domain'] == 'v.redd.it':
                    return data['url_overridden_by_dest']
                # everything else
                else:
                    await message.reply(data['url_overridden_by_dest'])
        return None

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        loop = asyncio.get_running_loop()
        if message.guild is None or message.author == self.bot.user:
            return
        if not (await self.bot.db.get_guild_data(message.guild.id)).config.tikTok:
            return
        content = (await self.convert_reddit(message)) or message.content
        matches = None

        for regex in REGEXES:
            matches = regex.match(content)
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

                    if os.path.getsize(f'{message.id}.mp4') > message.guild.filesize_limit:
                        loop.create_task(message.add_reaction('🪄'))  # magic wand

                        async with self.encode_lock:
                            task = partial(self.transcode_shrink, message.id, message.guild.filesize_limit * 0.95)
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
                log.warn(f'Exception occurred processing video {e} -- {os.path.getsize(f"{message.id}.mp4")}')

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
    def transcode_shrink(id, limit: int):
        shutil.copyfile(f'{id}.mp4', 'in.mp4')
        os.remove(f'{id}.mp4')
        limit = limit * 8
        try:
            video_length = math.ceil(float(subprocess.check_output(FFPROBE_CMD.split(' ')).decode("utf-8")))

            if video_length > MAX_VIDEO_LENGTH:
                raise commands.CommandInvokeError('Video is too large.')

            target_total_bitrate = limit / video_length
            buffer_size = math.floor(limit / BUFFER_CONSTANT)
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
                            file=discord.File(f"{ctx.message.id}.m4a", filename=f'{slugify(title)}.m4a'),
                            reference=ctx.message,
                        )
                    except discord.errors.HTTPException:
                        return await ctx.send("file too large :(", reference=ctx.message)
                    await ctx.send(
                        f"!play {msg.attachments[0].url}",
                    )
                finally:
                    if os.path.exists(f"{ctx.message.id}.m4a"):
                        os.remove(f"{ctx.message.id}.m4a")


def setup(bot):
    bot.add_cog(Video_DL(bot))
