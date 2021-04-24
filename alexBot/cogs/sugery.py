import logging
import math
from typing import TYPE_CHECKING

import aiohttp
from discord.ext import tasks

from alexBot.classes import SugeryZone, Thresholds

from ..tools import Cog, get_json

if TYPE_CHECKING:
    from bot import Bot


log = logging.getLogger(__name__)


# https://github.com/nightscout/cgm-remote-monitor/blob/0aed5c93a08b2483e4bb53f988b347a34b55321a/lib/plugins/direction.js#L53

DIR2CHAR = {
    "NONE": '⇼',
    "TripleUp": '⤊',
    "DoubleUp": '⇈',
    "SingleUp": '↑',
    "FortyFiveUp": '↗',
    "Flat": '→',
    "FortyFiveDown": '↘',
    "SingleDown": '↓',
    "DoubleDown": '⇊',
    "TripleDown": '⤋',
    'NOT COMPUTABLE': '-',
    'RATE OUT OF RANGE': '⇕',
}


class Sugery(Cog):
    def __init__(self, bot: "Bot"):
        super().__init__(bot)
        self.sugery_update.start()

    @tasks.loop(minutes=5)
    async def sugery_update(self):
        for user in self.bot.config.suggery:
            async with aiohttp.ClientSession() as session:
                data = await get_json(session, f"{user.baseURL}/api/v1/entries/current.json")
                device = await get_json(session, f"{user.baseURL}/api/v1/deviceStatus.json")
                log.debug(f"fetching {user.user}'s current data..")
                try:
                    sgv = data[0]['sgv']
                    direction = data[0]['direction']
                    battery = device[0]['uploader']['battery']
                except IndexError:
                    continue

                log.debug(f"{sgv=}, {user.thresholds=}")
                name = None
                zone = None
                if sgv <= user.thresholds.veryLow:
                    zone = SugeryZone.VERYLOW
                elif user.thresholds.veryLow <= sgv <= user.thresholds.low:
                    zone = SugeryZone.LOW
                elif user.thresholds.low <= sgv <= user.thresholds.high:
                    zone = SugeryZone.NORMAL
                elif user.thresholds.high <= sgv <= user.thresholds.veryHigh:
                    zone = SugeryZone.HIGH
                elif user.thresholds.veryHigh <= sgv:
                    zone = SugeryZone.VERYHIGH

                name = f"{user.names[zone]} {DIR2CHAR[direction]}"

                member = self.bot.get_guild(user.guild).get_member(user.user)
                if zone != user.lastGroup:
                    await member.send(
                        f"Hi! your sugery zone is now `{zone.name.lower()}`.\n"
                        f"your SGV is currently {sgv}.\n"
                        f"additionally, your phone battery is {battery}. \n"
                        f"the direction is {direction} ({DIR2CHAR[direction]})"
                    )
                if battery < 20 and not zone == user.lastGroup:
                    await member.send(f"ur battery dyin friendo: {battery}%")
                user.lastGroup = zone

                if member.nick == f"{name} (\N{BATTERY}{' ⡀⣀⣄⣤⣦⣶⣷⣿'[math.ceil(battery/9)]})":
                    continue

                await member.edit(
                    nick=f"{name} (\N{BATTERY}{' ⡀⣀⣄⣤⣦⣶⣷⣿'[math.ceil(battery/9)]})",
                    reason="user's bloodsuger group or direction changed",
                )

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
                    low=t['bgTargetBottom'],
                    veryLow=t['bgLow'],
                )
        await self.bot.wait_until_ready()

    def cog_unload(self):
        self.sugery_update.cancel()


def setup(bot):
    bot.add_cog(Sugery(bot))
