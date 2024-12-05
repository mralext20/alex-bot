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


# result of the bash expansion for `{m,h,w}{,x,g,b,a}`
ROLL_COMMANDS = "m mx mg mb ma h hx hg hb ha w wx wg wb wa".split()

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
        self.addSeriesFromRollMenu = app_commands.ContextMenu(
            name='Add Series to Liked',
            callback=self.addSeriesFromRoll,
        )
        self.removeSeriesFromRollMenu = app_commands.ContextMenu(
            name='Remove Series from Liked',
            callback=self.removeSeriesFromRoll,
        )
        self.removeSeriesCommand = app_commands.Command(
            callback=self.removeSeriesViaCommand,
            name='remove_series',
            description='Remove a series from your liked series',
        )

    async def cog_load(self) -> None:
        commands = [
            self.seriesExtractMenu,
            self.addSeriesFromRollMenu,
            self.removeSeriesFromRollMenu,
            self.removeSeriesCommand,
        ]
        for command in commands:
            self.bot.tree.add_command(command, guilds=[discord.Object(GAMESERVER)])

    async def cog_unload(self) -> None:
        commands = [
            self.seriesExtractMenu,
            self.addSeriesFromRollMenu,
            self.removeSeriesFromRollMenu,
            self.removeSeriesCommand,
        ]
        for command in commands:
            self.bot.tree.remove_command(command.name, type=command.type)

    async def series_autocomplete(self, interaction: discord.Interaction, guess: str) -> List[app_commands.Choice]:
        async with db.async_session() as session:
            series = await session.scalars(
                sqlalchemy.select(db.MudaeSeriesRequest.series).where(
                    sqlalchemy.and_(
                        db.MudaeSeriesRequest.requestedBy == interaction.user.id,
                        db.MudaeSeriesRequest.series.ilike(f'%{guess}%'),
                    )
                )
            )
        return [app_commands.Choice(name=s, value=s) for s in series]

    @app_commands.autocomplete(series=series_autocomplete)
    async def removeSeriesViaCommand(self, interaction: discord.Interaction, series: str):
        async with db.async_session() as session:
            await session.execute(
                sqlalchemy.delete(db.MudaeSeriesRequest).where(
                    sqlalchemy.and_(
                        db.MudaeSeriesRequest.series == series,
                        db.MudaeSeriesRequest.requestedBy == interaction.user.id,
                    )
                )
            )
            await session.commit()
        await interaction.response.send_message(
            f"removed {series} from your liked series!\n Don't forget to also $lmr {series}", ephemeral=True
        )

    async def addSeriesFromRoll(self, interaction: discord.Interaction, message: discord.Message):
        if message.author.id != MUDAE_BOT:
            await interaction.response.send_message("you need to run $m and right click *that* message", ephemeral=True)
            return
        if not message.embeds or not message.embeds[0].author or not message.embeds[0].author.name:
            await interaction.response.send_message("This message does not contain an embed.", ephemeral=True)
            return
        # try extract series name
        series_name = regex.findall(r'(.+\n?.+)\n?\*\*\d', message.embeds[0].description)[0].replace('\n', ' ')
        async with db.async_session() as session:
            await session.merge(db.MudaeSeriesRequest(series=series_name, requestedBy=interaction.user.id))
            await session.commit()
        await interaction.response.send_message(
            f"added {series_name} to your liked series!\nDon't forget to `$likem {series_name}`!", ephemeral=True
        )

    async def removeSeriesFromRoll(self, interaction: discord.Interaction, message: discord.Message):
        if message.author.id != MUDAE_BOT:
            await interaction.response.send_message("you need to run $m and right click *that* message", ephemeral=True)
            return
        if not message.embeds or not message.embeds[0].author or not message.embeds[0].author.name:
            await interaction.response.send_message("This message does not contain an embed.", ephemeral=True)
            return
        # try extract series name
        series_name = regex.findall(r'(.+\n?.+)\n?\*\*\d', message.embeds[0].description)[0].replace('\n', ' ')
        async with db.async_session() as session:
            await session.execute(
                sqlalchemy.delete(db.MudaeSeriesRequest).where(
                    sqlalchemy.and_(
                        db.MudaeSeriesRequest.series == series_name,
                        db.MudaeSeriesRequest.requestedBy == interaction.user.id,
                    )
                )
            )
            await session.commit()
        await interaction.response.send_message(
            f"removed {series_name} from your liked series!\n Don't forget to also $lmr {series_name}", ephemeral=True
        )

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.channel.id != PRIMARY_COMMAND_CHANNEL:
            return
        rolling_message = False
        if message.content.lower()[1:] in ROLL_COMMANDS:
            self.bot.loop.create_task(self.message_series_detector(message))
            rolling_message = True
        elif (
            message.author.id == MUDAE_BOT and message.interaction and message.interaction.name in ROLL_COMMANDS
        ):  # if mudae posts a message from an interaction for the slash command versions of the mudae commands, do the things too
            self.bot.loop.create_task(self.message_series_detector(message, actual_message=message))
            rolling_message = True
        if not rolling_message:
            return
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

    async def message_series_detector(self, message: discord.Message, actual_message: Optional[discord.Message] = None):
        if actual_message is None:
            actual_message = await self.bot.wait_for(
                "message",
                check=lambda m: m.author.id == MUDAE_BOT and m.channel.id == message.channel.id and len(m.embeds) == 1,
                timeout=5,
            )

        # get the series name from the embed
        embed = actual_message.embeds[0]
        description = embed.description
        assert description
        is_collectable = not (embed.footer and embed.footer.icon_url)
        series_name = regex.findall(r'(.+\n?.+)\n\*\*\d', description)[0].replace('\n', ' ')
        if is_collectable:
            async with db.async_session() as session:
                matches = await session.scalars(
                    sqlalchemy.select(db.MudaeSeriesRequest).where(db.MudaeSeriesRequest.series == series_name)
                )
                mentions = [f"<@{match.requestedBy}>" for match in matches]
                if mentions:
                    await actual_message.reply(
                        f"The series **{series_name}** (Character ***{embed.author.name}***) is Liked by {', '.join(mentions)}!",
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
            return
        if 'Liked Series' not in message.embeds[0].author.name:  # type: ignore
            await interaction.response.send_message(
                "This is not a $ml response. please right click on the message from $ml.", ephemeral=True
            )
            return

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

            await self._scan_pages(message, serieses, current_page, total_pages)
        else:
            serieses.extend(SERIES_REGEX.findall(message.embeds[0].description))  # type: ignore
            # captures single page

        async with db.async_session() as session:
            existing = await session.scalars(
                sqlalchemy.select(db.MudaeSeriesRequest).where(db.MudaeSeriesRequest.requestedBy == interaction.user.id)
            )
            existing = [e.series for e in existing]
            await session.execute(
                sqlalchemy.delete(db.MudaeSeriesRequest).where(db.MudaeSeriesRequest.requestedBy == interaction.user.id)
            )
            for series in serieses:
                await session.merge(db.MudaeSeriesRequest(series=series, requestedBy=interaction.user.id))
            await session.commit()
        reply_text = f"set your series to {len(serieses)} liked series!"
        changes = [f"added {series}" for series in serieses if series not in existing]
        changes.extend(f"removed {series}" for series in existing if series not in serieses)
        if len(changes) > 0 and len(changes) < 20:
            reply_text += f"\n{', '.join(changes)}"
        if interaction.response.is_done():
            await interaction.followup.send(reply_text, ephemeral=True)
        else:
            await interaction.response.send_message(reply_text, ephemeral=True)

    async def _scan_pages(self, message, serieses, current_page, total_pages):
        while current_page < total_pages:
            # get the next page
            payload = await self.bot.wait_for(
                "raw_message_edit",
                check=lambda payload: payload.message_id == message.id,
                timeout=60,
            )
            serieses.extend(SERIES_REGEX.findall(payload.data['embeds'][0]['description']))  # type: ignore ; checked above if embed exists
            # captures pages 2 thru n
            current_page += 1
            if current_page == total_pages:
                break


async def setup(bot: "Bot"):
    await bot.add_cog(Mudae(bot))
