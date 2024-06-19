import asyncio
import logging
from typing import TYPE_CHECKING, List

import discord
from discord import app_commands
from datetime import datetime, timedelta

import regex
import sqlalchemy

from ..tools import Cog

from typing import Optional

from alexBot import database as db

if TYPE_CHECKING:
    from bot import Bot


log = logging.getLogger(__name__)

GAMESERVER = 1069353044808056902
PRIMARY_COMMAND_CHANNEL = 1077272164887183450
MENTION_ROLE = 1251159714532691979
MUDAE_BOT = 432610292342587392

SERIES_REGEX = regex.compile(r'\*\*\d{1,3} - (.+)\*\*')


class Mudae(Cog):
    def __init__(self, bot: "Bot"):
        super().__init__(bot)
        self.lastPinged: Optional[datetime] = None
        self.lastMessage: Optional[datetime] = None
        self.seriesExtractMenu = app_commands.ContextMenu(
            name='Extract Liked Series',
            callback=self.extract_series,
        )

    async def cog_load(self) -> None:
        self.bot.tree.add_command(
            self.seriesExtractMenu,
            guilds=[
                discord.Object(GAMESERVER),
            ],
        )

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.channel.id != PRIMARY_COMMAND_CHANNEL:
            return
        if message.content.lower() in ["$m", "$mg", "$ma"]:
            self.bot.loop.create_task(self.message_series_detector(message))
            if self.lastMessage is None:
                self.lastMessage = datetime.now()
            elif datetime.now() - self.lastMessage < timedelta(seconds=60):
                self.lastMessage = datetime.now()
                return

            if self.lastPinged is None:
                self.lastPinged = datetime.now()
            elif datetime.now() - self.lastPinged < timedelta(minutes=5):
                return
            self.lastPinged = datetime.now()
            await message.channel.send(f"<@&{MENTION_ROLE}>", allowed_mentions=discord.AllowedMentions(roles=True))

    async def message_series_detector(self, message: discord.Message):
        msg = await self.bot.wait_for(
            "message",
            check=lambda m: m.author.id == MUDAE_BOT and m.channel.id == PRIMARY_COMMAND_CHANNEL and len(m.embeds) == 1,
        )
        # get the series name from the embed
        description = msg.embeds[0].description
        assert description
        is_collectable = "React with any emoji to claim!" in description
        series_name = description.split("\n")[0]
        if is_collectable:
            async with db.async_session() as session:
                matches = await session.scalars(
                    sqlalchemy.select(db.MudaeSeriesRequest).where(db.MudaeSeriesRequest.series == series_name)
                )
                mentions = [f"<@{match.requestedBy}>" for match in matches]
                if mentions:
                    await msg.reply(
                        f"The series {series_name} is Liked by {', '.join(mentions)}!",
                        allowed_mentions=discord.AllowedMentions(users=True),
                    )

    async def extract_series(self, interaction: discord.Interaction, message: discord.Message):
        # user will be from the interaction
        # series can be extracted from the message clicked on
        # need to loop on message updates, check footer for competion 'Page n / n'
        # there may be no footer, can validated liked series page by checking author field

        if message.author.id != MUDAE_BOT:
            await interaction.response.send_message(
                "you need to run $ml and right click *that* message", ephemeral=True
            )
        # it's a mudae message! check if it's a liked series message
        if not message.embeds or not message.embeds[0].author or not message.embeds[0].author.name:
            await interaction.response.send_message("This message does not contain an embed.", ephemeral=True)
        if 'Liked Series' not in message.embeds[0].author.name:  # type: ignore
            await interaction.response.send_message(
                "This is not a $ml response. please right click on the message from $ml.", ephemeral=True
            )

        serieses: List[str] = []
        # it's a message we care about! do we have a paginator?
        if message.embeds[0].footer:
            assert isinstance(message.embeds[0].footer.text, str)
            if 'Page' not in message.embeds[0].footer.text:
                await interaction.response.send_message("This shound not happen...", ephemeral=True)
            # extract page details:
            regex_result = regex.match(r'Page (\d+) / (\d+)', message.embeds[0].footer.text)
            if not regex_result:
                await interaction.response.send_message("This should not happen...", ephemeral=True)
                return
            current_page, total_pages = regex_result.groups()
            current_page, total_pages = int(current_page), int(total_pages)
            if current_page != 1:
                await interaction.response.send_message("Please start from the first page.", ephemeral=True)
                return
            serieses.extend(SERIES_REGEX.findall(message.embeds[0].description))  # type: ignore
            # ^ captures first page
            await interaction.response.send_message("tab through your liked series, i'll save them!", ephemeral=True)

            while current_page < total_pages:

                # get the next page
                payload = await self.bot.wait_for(
                    "raw_message_edit",
                    check=lambda payload: payload.message_id == message.id,
                    timeout=60,
                )
                serieses.extend(SERIES_REGEX.findall(payload.data['embeds'][0]['description']))
                # captures pages 2 thru n
                current_page += 1
                if current_page == total_pages:
                    break
        else:
            serieses.extend(SERIES_REGEX.findall(message.embeds[0].description))  # type: ignore
            # captures single page

        async with db.async_session() as session:
            await session.execute(
                sqlalchemy.delete(db.MudaeSeriesRequest).where(db.MudaeSeriesRequest.requestedBy == interaction.user.id)
            )
            for series in serieses:
                await session.merge(db.MudaeSeriesRequest(series=series, requestedBy=interaction.user.id))
            await session.commit()
        if interaction.response.is_done():
            await interaction.followup.send(f"added {len(serieses)} liked series!", ephemeral=True)
        else:
            await interaction.response.send_message(f"added {len(serieses)} liked series!", ephemeral=True)


async def setup(bot: "Bot"):
    await bot.add_cog(Mudae(bot))
