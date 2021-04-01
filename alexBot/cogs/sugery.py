import logging

import aiohttp
from discord.ext import tasks

from alexBot.classes import Thresholds

from ..tools import Cog, get_json

log = logging.getLogger(__name__)


class Sugery(Cog):
    def __init__(self, bot):
        super().__init__(bot)
        self.sugery_update.start()

    @tasks.loop(minutes=5)
    async def sugery_update(self):
        for user in self.bot.config.suggery:
            async with aiohttp.ClientSession() as session:
                data = await get_json(session, f"{user.baseURL}/api/v1/entries/sgv.json")
                log.debug(f"fetching {user.user}'s current data..")

                sgv = data[0]['sgv']
                name = None
                if sgv <= user.thresholds.veryLow:
                    # verylow
                    name = user.veryLowSugerName
                elif user.thresholds.veryLow <= sgv <= user.thresholds.low:
                    name = user.lowSugerName
                elif user.thresholds.low <= sgv <= user.thresholds.high:
                    name = user.normalSugerName
                elif user.thresholds.high <= sgv <= user.thresholds.veryHigh:
                    name = user.highSugerName
                elif user.thresholds.veryHigh <= sgv:
                    name = user.veryHighSugerName

                if name == user.lastName:
                    break
                user = self.bot.get_guild(user.guild).get_member(user.user)
                await user.edit(nick=name, reason="user's bloodsuger group changed")

    @sugery_update.before_loop
    async def before_sugery(self):
        for user in self.bot.config.suggery:
            async with aiohttp.ClientSession() as session:
                data = await get_json(session, f"{user.baseURL}/api/v1/status.json")
                log.debug(f"fetching {user.user}..")
                t = data['settings']['thresholds']
                user.thresholds = Thresholds(
                    veryHigh=t['bgHigh'],
                    high=t['bgTargetTop'],
                    low=t['bgTargetTop'],
                    veryLow=t['bgLow'],
                )


def setup(bot):
    bot.add_cog(Sugery(bot))
