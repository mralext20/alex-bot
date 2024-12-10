import logging
import re
import time
from typing import Dict, List

import aiohttp
import discord
from discord import MessageType, PartialEmoji, app_commands, ui
from discord.ext import commands
from emoji_data import EmojiSequence
from sqlalchemy import select

from alexBot import database as db

from ..tools import Cog, get_json

log = logging.getLogger(__name__)
AYYGEN = re.compile("[aA][yY][Yy][yY]*")
YOUTUBE_REGEX = re.compile(r"https?:\/\/(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([\w-]{11})")
VOTE_EMOJIS = ["<:greentick:1074791788205854731>", "<:yellowtick:872631240010899476>", "<:redtick:968969232870178896>"]


class Fun(Cog):
    def __init__(self, bot):
        super().__init__(bot)
        self.EMOJI_REGEX = re.compile(r"<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>")
        self.FALLBACK_EMOJI_REGEX = re.compile(
            r":(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>\d{18,22})>>"
        )  # matches :a?:name:ID>> for manual addition from emoji ID. the a is indicating if the emoji is animated or not
        self.last_posted: Dict[int, float] = {}

        self.stealEmojiMenu = app_commands.ContextMenu(
            name='Steal Emojis',
            callback=self.stealEmoji,
        )

        self.recentlyReminded: List[int] = []

    async def cog_load(self) -> None:
        self.bot.tree.add_command(
            self.stealEmojiMenu,
            guilds=[
                discord.Object(791528974442299412),
                discord.Object(384843279042084865),
                discord.Object(1083141160198996038),
                discord.Object(1220224297235251331),
                discord.Object(383886323699679234),
            ],
        )

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.stealEmojiMenu.name, type=self.stealEmojiMenu.type)

    async def stealEmoji(self, interaction: discord.Interaction, message: discord.Message):
        raw_emojis = self.EMOJI_REGEX.findall(message.content)
        raw_emojis += self.FALLBACK_EMOJI_REGEX.findall(message.content)
        emojis = [
            PartialEmoji.with_state(self.bot._connection, animated=(e[0] == 'a'), name=e[1], id=e[2])
            for e in raw_emojis
        ]
        if len(emojis) == 0:
            if len(message.stickers) > 0:
                await self.stealSticker(interaction, message)
            else:
                await interaction.response.send_message("there's no Emoji to steal :(", ephemeral=True)
            return
        bot = self.bot

        class IndexSelector(ui.Select):
            def __init__(
                self,
                og_message: discord.Message,
            ):
                super().__init__(
                    placeholder="Select Emoji to steal...",
                    min_values=1,
                    options=[
                        discord.SelectOption(label=e.name, value=str(index), emoji=PartialEmoji.from_dict(e.to_dict()))
                        for index, e in enumerate(emojis)
                    ],
                    max_values=len(emojis),
                )
                self.og_message = og_message

            async def callback(self, interaction: discord.Interaction):
                await interaction.response.send_message("i'll get right on that!", ephemeral=True)
                uploads = []

                for i in self.values:
                    index = int(i)
                    emoji = emojis[index]
                    data = await emoji.read()
                    uploaded = await interaction.guild.create_custom_emoji(name=emoji.name, image=data)
                    await interaction.followup.send(f"{uploaded}", ephemeral=True)
                    uploads.append(f"{uploaded}")

                await self.og_message.reply(
                    f"{'these are' if len(uploads) > 1 else 'this is'} mine now\n\n{' '.join(uploads)}"
                )

        class EmojiSelector(ui.View):
            def __init__(self):
                super().__init__(timeout=60)
                self.add_item(IndexSelector(message))

        await interaction.response.send_message(view=EmojiSelector(), ephemeral=True)

    async def stealSticker(self, interaction: discord.Interaction, msg: discord.Message):
        stick = await msg.stickers[0].fetch()
        if interaction.guild is None:
            # piss
            return
        await interaction.response.send_message("i'll get right on that!", ephemeral=True)
        payload = {}
        payload['name'] = stick.name
        payload['description'] = stick.description
        payload['emoji'] = stick.emoji
        payload['tags'] = 'stolen'
        rawstick = await stick._state.http.create_guild_sticker(
            guild_id=interaction.guild.id, payload=payload, file=await stick.to_file(), reason="stealing sticker"
        )
        newstick = discord.GuildSticker(state=stick._state, data=rawstick)
        await interaction.channel.send("This is mine now", stickers=[newstick])

    @app_commands.command(name="cat")
    async def slash_cat(self, interaction: discord.Interaction):
        """Posts a pretty photo of a cat"""
        async with aiohttp.ClientSession() as session:
            self.bot.loop.create_task(interaction.response.defer(thinking=True))
            cat = await get_json(
                session,
                f"https://thecatapi.com/api/images/get?format=json" f"&api_key={self.bot.config.cat_token}",
            )
            cat = cat[0]
            embed = discord.Embed()
            embed.set_image(url=cat["url"])
            embed.url = "http://thecatapi.com"
            embed.title = "cat provided by the cat API"
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="dog")
    async def dog(self, interaction: discord.Interaction):
        """Posts a pretty picture of a dog."""
        self.bot.loop.create_task(interaction.response.defer(thinking=True))
        async with aiohttp.ClientSession() as session:
            dog = None
            while dog is None or dog["url"][-3:].lower() == "mp4":
                dog = await get_json(session, "https://random.dog/woof.json")
                log.debug(dog["url"])
            ret = discord.Embed()
            ret.set_image(url=dog["url"])
            await interaction.followup.send(embed=ret)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is None:
            return
        cfg = None
        async with db.async_session() as session:
            cfg = await session.scalar(select(db.GuildConfig).where(db.GuildConfig.guildId == message.guild.id))
            if not cfg:
                # we need to create a new default config for this guild
                async with session.begin():
                    cfg = db.GuildConfig(guildId=message.guild.id)
                    session.add(cfg)
        if cfg.ayy:
            if AYYGEN.fullmatch(message.content):
                await message.reply("lmao", mention_author=False)
        if cfg.veryCool:
            if message.content.lower().startswith("thank you "):
                await message.reply("very cool", mention_author=False)
        if cfg.firstAmendment:
            if any([check in message.content.lower() for check in ["free speech", "first amendment"]]):
                if self.last_posted.get(message.channel.id, time.time() - 60 * 60 * 24) < time.time() - 60 * 60:
                    await message.reply("https://xkcd.com/1357/", mention_author=True)
                    self.last_posted[message.channel.id] = time.time()

        # bespoke thing, maybe make config and guild based in the future
        if message.channel.id == 847555306166943755:
            if message.type == MessageType.thread_created:
                await message.delete()  # thread creation messages delete without sending a message
                return
            if message.content.endswith('??'):
                # don't do anything, question is intending a thread
                return
            emojis = VOTE_EMOJIS
            raw_emojis = EmojiSequence.pattern.findall(message.content)

            matches = self.EMOJI_REGEX.findall(message.content)
            if matches or raw_emojis:
                emojis = [
                    PartialEmoji.with_state(self.bot._connection, animated=(e[0] == 'a'), name=e[1], id=e[2])
                    for e in matches
                ]
                emojis += raw_emojis

            if message.content.endswith('?') or emojis != VOTE_EMOJIS:
                for emoji in emojis:
                    try:
                        await message.add_reaction(emoji)
                    except discord.DiscordException:
                        if isinstance(emoji, PartialEmoji):
                            # steal the emoji temporarily to react with it
                            data = await emoji.read()
                            nerdiowo = self.bot.get_guild(791528974442299412)
                            uploaded = await nerdiowo.create_custom_emoji(
                                name=emoji.name, image=data, reason="temporily added for #everybody-votes"
                            )
                            await message.add_reaction(uploaded)
                            await uploaded.delete(reason="removed from temp addition")

                return
            else:
                try:
                    await message.author.send(
                        "Your message was deleted. please end it with a `?`\n\nYour original content is here:"
                    )
                    await message.author.send(message.content)
                except discord.DiscordException:
                    pass

                await message.delete()


async def setup(bot):
    await bot.add_cog(Fun(bot))
