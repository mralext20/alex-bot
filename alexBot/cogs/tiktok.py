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
tiktok = re.compile(r'https?://vm\.tiktok\.com/.{6,}/')
reddit = re.compile(r'https?://v\.redd\.it/.{13,}')
opts = {'outtmpl': 'out.mp4'}
ytdl = YoutubeDL(opts)


class TikTok(Cog):
    active = False

    @staticmethod
    def download_tiktok(url, source):
        data = ytdl.extract_info(url, download=True)
        return data['title'] if source == 'tiktok' else ''

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is None:
            return
        if (await get_guild_config(self.bot, message.guild.id))['tikTok'] is False:
            return
        match_from = 'tiktok'
        matches = tiktok.match(message.content)
        if matches is None:
            matches = reddit.match(message.content)
            match_from = 'reddit'
            if matches is None:
                return

        match = matches.group(0)
        log.info(f'collecting {match} for {message.author}')

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
                task = partial(self.download_tiktok, match, match_from)
                title = await self.bot.loop.run_in_executor(None, task)
                if os.path.getsize('out.mp4') > 8000000:
                    try:
                        await message.remove_reaction('⌛', self.bot.user)
                        await message.add_reaction('❌')
                    except discord.Forbidden:
                        await message.channel.send('too large too send')
                else:
                    # file is out.mp4, need to create discord.File and upload it to channel then delete out.mp4
                    file = discord.File('out.mp4', 'tiktok.mp4' if match_from == 'tiktok' else 'vid.mp4')
                    await message.channel.send(title, file=file)
                    await message.remove_reaction('⌛', self.bot.user)
                    await message.add_reaction('✅')

        finally:
            self.active = False
            os.remove('out.mp4')


def setup(bot):
    bot.add_cog(TikTok(bot))
