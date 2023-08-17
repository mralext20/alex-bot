import logging
import math
from typing import TYPE_CHECKING

import aiohttp
import discord
from discord.ext import tasks

from alexBot.classes import SugeryTranslations, SugeryZone, Thresholds
from alexBot.database import SugeryUser, async_session, select

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

BATTERYINDICATORS = " \U00002840\U000028c0\U000028c4\U000028e4\U000028e6\U000028f6\U000028f7\U000028ff"

ZAPSTR = "\N{HIGH VOLTAGE SIGN}"
BATTERYSTR = "\N{BATTERY}"


class Sugery(Cog):
    def __init__(self, bot: "Bot"):
        super().__init__(bot)
        self.sugery_update.start()

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if isinstance(message.channel, discord.DMChannel):
            # get the user

            async with async_session() as session:
                userData = await session.scalar(select(SugeryUser).where(SugeryUser.userId == message.author.id))
                if not userData:
                    return
            async with aiohttp.ClientSession() as session:
                data = await get_json(session, f"{userData.baseURL}/api/v1/entries/current.json")
                device = await get_json(session, f"{userData.baseURL}/api/v1/deviceStatus.json")
                log.debug(f"fetching {userData.userId}'s current data..")
                try:
                    sgv = data[0]['sgv']
                    direction = data[0]['direction']
                    battery = device[0]['uploader']['battery']
                    charging = (battery > device[1]['uploader']['battery']) or battery == 100
                except IndexError:
                    await message.channel.send("error :shrug:")
                    return

                await message.channel.send(
                    f"{battery=}, {charging=}( based on previous batery reading of {device[1]['uploader']['battery']}), {sgv=}, {direction=} ({DIR2CHAR[direction]})"
                )

    @tasks.loop(minutes=5)
    async def sugery_update(self):
        async with async_session() as session:
            sgus = await session.scalars(select(SugeryUser))
        for user in sgus:
            async with aiohttp.ClientSession() as session:
                data = await get_json(session, f"{user.baseURL}/api/v1/entries/current.json")
                device = await get_json(session, f"{user.baseURL}/api/v1/deviceStatus.json")
                log.debug(f"fetching {user.userId}'s current data..")
                try:
                    sgv = data[0]['sgv']
                    direction = data[0]['direction']
                    battery = device[0]['uploader']['battery']
                    charging = (battery > device[1]['uploader']['battery']) or battery == 100
                except IndexError:
                    continue

                log.debug(f"{sgv=}, {user.thresholds=}")
                name = None
                zone = None
                if not user.thresholds:
                    # uh oh
                    raise ValueError("sgv has not loaded threshholds somehow")
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
                if name is None or zone is None:
                    raise ValueError("name or zone is None")

                g = self.bot.get_guild(user.guildId)
                if not g:
                    log.error(f"cannot find guild {user.guildId}")
                    member = self.bot.get_user(user.userId)
                    if not member:
                        log.error(f"cannot find user {user.userId}")
                        continue
                else:
                    member = g.get_member(user.userId)
                    if not member:
                        member = self.bot.get_user(user.userId)
                        if not member:
                            log.error(f"cannot find user {user.userId}")
                            continue

                if zone != user.lastGroup:
                    await member.send(
                        f"Hi! your sugery zone is now `{user.names[zone]}`.\n"
                        f"your SGV is currently {sgv}.\n"
                        f"additionally, your phone battery is {battery}. \n"
                        f"the direction is {direction} ({DIR2CHAR[direction]})"
                    )
                if user.constantAlerts and zone != SugeryZone.NORMAL:
                    # we need to send a message to the constant alert reciver.
                    alert = self.bot.get_user(user.constantAlerts)
                    if alert:
                        await alert.send(
                            f"ALARM!! Mounir's Blutzuckerswert ist zu {SugeryTranslations[zone]} Der Blutzuckerwert ist {sgv}."
                        )
                    else:
                        log.error(f"cannot find user {user.constantAlerts} for constant alerts")
                        continue
                if battery < 30 and not zone == user.lastGroup:
                    await member.send(f"ur battery dyin friendo: {battery}%")
                user.lastGroup = zone
                if g:
                    try:
                        assert isinstance(member, discord.Member)
                        await member.edit(
                            nick=f"{name} ({ZAPSTR if charging else BATTERYSTR}{BATTERYINDICATORS[math.ceil(battery * 0.08)]})",
                            reason="user's bloodsuger group or direction changed",
                        )
                    except Exception as e:
                        log.error(f"cannot update {member}; {e.args[0]}")
                        continue

    @sugery_update.before_loop
    async def before_sugery(self):
        async with async_session() as session:
            sgus = await session.scalars(select(SugeryUser))
            for user in sgus:
                async with aiohttp.ClientSession() as http_session:
                    data = await get_json(http_session, f"{user.baseURL}/api/v1/status.json")
                    log.debug(f"fetching {user.userId}..")
                    t = data['settings']['thresholds']
                    user.thresholds = Thresholds(
                        veryHigh=t['bgHigh'],
                        high=t['bgTargetTop'],
                        low=t['bgTargetBottom'],
                        veryLow=t['bgLow'],
                    )
                    session.add(user)
            await session.commit()
            await self.bot.wait_until_ready()

    def cog_unload(self):
        self.sugery_update.cancel()


async def setup(bot):
    await bot.add_cog(Sugery(bot))
