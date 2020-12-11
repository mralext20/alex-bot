import logging
import re
from functools import partial
import discord
from discord.ext import commands
import os
import shutil
import asyncio
import subprocess
import math
from ..tools import Cog
from ..tools import get_guild_config
from youtube_dl import YoutubeDL

log = logging.getLogger(__name__)
REGEXES = [
    re.compile(r'https?://vm\.tiktok\.com/.{6,}/'),
    re.compile(r'https?://(?:v\.)?redd\.it/.{6,}'),
    re.compile(r'https?://(?:\w{,32}\.)?reddit\.com\/(?:r\/\w+\/)?comments\/.{6,}')
]

ytdl = YoutubeDL({'outtmpl': 'out.mp4'})

TARGET_SHRINK_SIZE = (8*10**6 - 128*1000) * 8 # 8 MB - 128 KB in bits
MAX_VIDEO_LENGTH = 5 * 60 # 5 Minutes
AUDIO_BITRATE = 64 * 1000 # 64 Kbits
BUFFER_CONSTANT = 20 # Magic number, see https://unix.stackexchange.com/a/598360

FFPROBE_CMD = 'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 in.mp4'
FFMPEG_CMD  = 'ffmpeg -i in.mp4 -y -b:v {0} -maxrate:v {0} -b:a {1} -maxrate:a {1} -bufsize:v {2} out.mp4'


class Video_DL(Cog):
    active = False

    @staticmethod
    def download_video(url):
        data = ytdl.extract_info(url, download=True)
        return data['title'] 

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is None:
            return
        if (await get_guild_config(self.bot, message.guild.id))['tikTok'] is False:
            return
        
        matches = None

        for regex in REGEXES:
            matches = regex.match(message.content)
            if matches: break

        if matches is None: return

        match = matches.group(0)
        log.info(f'collecting {match} for {message.author}')
        async with message.channel.typing():
            while self.active:
                await asyncio.sleep(.5)
            try:
                self.active = True
                if match:
                    await message.channel.trigger_typing()
                    try:
                        await message.add_reaction('⌛')
                    except discord.Forbidden:
                        pass
                    
                    task = partial(self.download_video, match)
                    title = await self.bot.loop.run_in_executor(None, task)
                    
                    if os.path.getsize('out.mp4') > 8000000:
                        try:
                            await message.add_reaction('🪄')
                        except: pass

                        await self.bot.loop.run_in_executor(None, self.transcode_shrink)
                    
                    # file is out.mp4, need to create discord.File and upload it to channel then delete out.mp4
                    file = discord.File('out.mp4', 'vid.mp4')

                    await message.channel.send(title, file=file)
                    
                    try:
                        await message.add_reaction('✅')
                    except: pass

            except Exception as e:
                log.warn(f'Exception occurred processing video {e}')

                try:
                    await message.add_reaction('❌')
                except discord.Forbidden:
                    await message.channel.send('Something broke')

            finally:
                await message.remove_reaction('⌛', self.bot.user)
                self.active = False

                if os.path.exists('out.mp4'):
                    os.remove('out.mp4')


    @staticmethod
    def transcode_shrink():
        shutil.copyfile('out.mp4', 'in.mp4')
        os.remove('out.mp4')

        try:
            input_filesize = os.path.getsize('in.mp4')
            video_length = float(subprocess.check_output(FFPROBE_CMD.split(' ')).decode("utf-8"))
            
            if video_length > MAX_VIDEO_LENGTH:
                raise commands.CommandInvokeError('Video is too large.')

            target_total_bitrate = TARGET_SHRINK_SIZE / video_length
            buffer_size = math.floor(TARGET_SHRINK_SIZE / BUFFER_CONSTANT)
            target_video_bitrate = target_total_bitrate - AUDIO_BITRATE
                
            command_formatted = FFMPEG_CMD.format(
                str(target_video_bitrate),
                str(AUDIO_BITRATE),
                str(buffer_size)
            )

            subprocess.check_call(command_formatted.split(' '))
            
        except Exception as e:
            log.warn(f'Exception occurred transcoding video {e}')

        finally:
            if os.path.exists('in.mp4'):
                os.remove('in.mp4')

def setup(bot):
    bot.add_cog(Video_DL(bot))
