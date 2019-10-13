import logging
import re
from functools import partial
import discord
from discord.ext import commands
import os
import asyncio
from ..tools import Cog
from ..tools import get_guild_config
from youtube_dl import YoutubeDL

log = logging.getLogger(__name__)
tiktok = re.compile(r'http://vm.tiktok.com/.{6,}/')
opts = {'outtmpl': 'out.mp4'}
ytdl = YoutubeDL(opts)


class TikTok(Cog):
    active = False
    @staticmethod
    def download_tiktok(url):
        return ytdl.download([url])

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild is None:
            return
        if (await get_guild_config(self.bot, message.guild.id))['tikTok'] is False:
            return
        matches = tiktok.match(message.content)
        if matches is None:
            return
        match = matches.group(0)
        while self.active:
            await asyncio.sleep(.5)
        try:
            self.active = True
            if match:
                await message.channel.trigger_typing()
                thing = partial(self.download_tiktok, match)
                await self.bot.loop.run_in_executor(None, thing)
                if os.path('out.mp4').size > 8000000:
                    await message.channel.send('i cant embed that, its too big :(')
                else:
                    # file is out.mp4, need to create discord.File and upload it to channel then delete out.mp4
                    file = discord.File('out.mp4', 'tiktok.mp4')
                    await message.channel.send(file=file)
        finally:
            os.remove('out.mp4')
            self.active = False


def setup(bot):
    bot.add_cog(TikTok(bot))
