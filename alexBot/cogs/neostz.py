# -*- coding: utf-8 -*-

import asyncio
import json
from dataclasses import asdict
from datetime import datetime
from typing import Dict, List, Optional

import discord
import pytz
from discord.ext import commands

from ..classes import NeosTZData, NeosUser
from ..tools import Cog, grouper, transform_neosdb

GUILD_GROUP_LOOKUP: Dict[int, str] = {
    670631606477651970: 'viarsys',
    97248702250360832: 'vibez',
    383886323699679234: 'viarsys',
}

REQUEST_USERNAME = "What is the username of your account in neos? you can say 'Alex' or 'U-alex_from_alaska'"
REQUEST_TIMEZONE = (
    "What timezone do you live in? see "
    "<http://www.timezoneconverter.com/cgi-bin/findzone> to help figure out your timezone, "
    "or <https://en.wikipedia.org/wiki/List_of_tz_database_time_zones> for just a plain list of timezones.\n\n"
    "please ensure that you are using a timezone with a `/` in it, e.g. `America/Anchorage`, `Europe/Berlin`"
)

DATA_PATH = "../neostz/data.json"


neosUserCache: Dict[str, NeosUser] = {}


class NeosTZ(Cog):

    """Set of commands to do with NeosTZ stuff"""

    RWLOCK = asyncio.Lock()

    def readData(self) -> NeosTZData:
        data = json.load(open(self.bot.config.neosTZData))
        return NeosTZData(data)

    def saveData(self, data: NeosTZData):
        str = json.dumps(asdict(data), indent=2)
        with open(self.bot.config.neosTZData, 'w') as f:
            f.write(str)

    async def confirm(self, msg: discord.Message, target: discord.Member):
        reactions = ["\U00002705", "\U0000274c"]
        await msg.add_reaction("\U00002705")  # WHITE HEAVY CHECK MARK
        await msg.add_reaction("\U0000274c")  # CROSS MARK
        reaction, member = await self.bot.wait_for(
            "reaction_add",
            check=lambda reaction, member: member == target and reaction.emoji in reactions,
            timeout=120,
        )
        [asyncio.get_event_loop().create_task(msg.remove_reaction(r, self.bot.user)) for r in reactions]
        return reaction.emoji == "\U00002705"

    @staticmethod
    def embed_for_user(user: NeosUser) -> discord.Embed:
        embed = discord.Embed()
        embed.set_author(name=user.username, icon_url=user.icon or embed.Empty)
        embed.color = discord.Color(0xF1C40F)  # solarix Gold ? citation needed
        embed.set_footer(text=f"user ID: {user.idx}")
        return embed

    async def get_neos_users(self, name: str) -> List[NeosUser]:
        if name.startswith("U-"):
            if ' ' in name:
                raise ValueError("can't have spaces in a U- based User ID")
            try:
                return neosUserCache[name]
            except KeyError:
                data = await self.bot.session.get(f"https://www.api.neos.com/api/users/{name}")
                try:
                    users = [NeosUser(await data.json())]
                except KeyError:
                    raise ValueError("Not Found")
        else:
            data = await self.bot.session.get("https://www.api.neos.com/api/users", params={'name': name})
            try:
                users = [NeosUser(data) for data in (await data.json())]
            except KeyError:
                raise ValueError("Not Found")
        return users

    def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.guild is not None and ctx.guild.id in GUILD_GROUP_LOOKUP

    @commands.group('neostz', invoke_without_command=True)
    async def neostz(self, ctx: commands.Context):
        """shows who's when in this group"""
        async with self.RWLOCK:
            data = self.readData()
        groupData = next(
            group for group in data.groups if group.name == GUILD_GROUP_LOOKUP[ctx.guild.id]
        )  # list.find(e.name == group)
        members = {(await self.get_neos_users(user))[0]: pytz.timezone(tz) for user, tz in groupData.users.items()}
        for group in grouper([(k, v) for k, v in members.items()], 25):
            embed = discord.Embed()
            embed.set_author(
                name=f"Times for Members of {groupData.name}",
                icon_url=(
                    transform_neosdb(groupData.default_icon)
                    if groupData.default_icon.startswith('neosdb:///')
                    else groupData.default_icon
                ),
            )

            embed.color = discord.Color(0xF1C40F)
            for member, timezone in group:
                embed.add_field(
                    name=member.username,
                    value=pytz.utc.localize(datetime.utcnow()).astimezone(timezone).strftime('%H:%M (%I:%M %p)'),
                )
            await ctx.send(embed=embed)

    @neostz.command()
    async def add(self, ctx: commands.Context):
        """add yourself or someone else to your group's data"""
        user: Optional[NeosUser] = None
        await ctx.send(REQUEST_USERNAME)
        # get username via req / ack, check & confirm w/ neosAPI
        while user is None:
            usermsg = await self.bot.wait_for(
                'message',
                check=lambda msg: msg.author.id == ctx.author.id and msg.channel.id == ctx.channel.id,
                timeout=120,
            )
            try:
                users = await self.get_neos_users(usermsg.content)
                for user in users:
                    msg = await ctx.send(content="is this the right user?", embed=self.embed_for_user(user))
                    if await self.confirm(msg, ctx.author):
                        break
                    else:
                        asyncio.get_event_loop().create_task(msg.delete())
                else:
                    await ctx.send(REQUEST_USERNAME)
            except ValueError as e:
                await ctx.send(f'try again, {e}\n{REQUEST_USERNAME}')

        # get timezone, confirm via localtime lookup
        tz = None
        await ctx.send(f"Great! {REQUEST_TIMEZONE}")
        while tz is None:
            usermsg = await self.bot.wait_for(
                'message',
                check=lambda msg: msg.author.id == ctx.author.id and msg.channel.id == ctx.channel.id,
                timeout=120,
            )
            try:
                if '/' not in usermsg.contnet:
                    raise pytz.UnknownTimeZoneError
                tz = pytz.timezone(usermsg.content)
                localtime = pytz.utc.localize(datetime.utcnow()).astimezone(tz)
                msg = await ctx.send(
                    f"too confirm, your timezone is {tz.zone}, and it is "
                    f"{localtime.strftime('%H:%M (%I:%M %p)')} where you live?"
                )
                if not await self.confirm(msg, ctx.author):
                    tz = None
            except pytz.UnknownTimeZoneError:
                tz = None
                await ctx.send(f"cannot find the timezone {usermsg.content}")

        await ctx.send(
            f"ok! your user account is {user.username}, and the TZ is {tz}. i'll go ahead and tell the panel in neos to update...."
        )
        # aquire lock
        async with self.RWLOCK:
            data = self.readData()
            group = next(
                group for group in data.groups if group.name == GUILD_GROUP_LOOKUP[ctx.guild.id]
            )  # list.find(e.name == group)
            group.users[user.idx] = str(tz)
            self.saveData(data)
        if self.bot.location != 'dev':
            process = await asyncio.create_subprocess_shell('systemctl start --user neos-tz.service')
            await process.wait()
            await ctx.send('updated!')


async def setup(bot):
    await bot.add_cog(NeosTZ(bot))
