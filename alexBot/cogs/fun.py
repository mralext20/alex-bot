import datetime
import logging
import random
import re
import time
from typing import Dict, List

import aiohttp
import discord
from discord import MessageType, PartialEmoji, app_commands, ui
from discord.ext import commands, tasks
from emoji_data import EmojiSequence

from ..tools import Cog, get_json

log = logging.getLogger(__name__)
AYYGEN = re.compile("[aA][yY][Yy][yY]*")
YOUTUBE_REGEX = re.compile(r"https?:\/\/(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([\w-]{11})")
VOTE_EMOJIS = ["<:greentick:1074791788205854731>", "<:yellowtick:872631240010899476>", "<:redtick:968969232870178896>"]
ARSON_STRINGS = ["fire", "arson", "kat", "cat", "arsn"]


class Fun(Cog):
    def __init__(self, bot: "Bot"):
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
        self.videoLengthMenu = app_commands.ContextMenu(
            name='How Long is this Video?',
            callback=self.videoLength,
        )

        self.recentlyReminded: List[int] = []

    async def cog_load(self) -> None:
        self.bot.tree.add_command(
            self.stealEmojiMenu,
            guilds=[
                discord.Object(791528974442299412),
                discord.Object(384843279042084865),
                discord.Object(1083141160198996038),
            ],
        )
        self.bot.tree.add_command(self.videoLengthMenu, guild=discord.Object(791528974442299412))
        self.bot.voiceCommandsGroup.add_command(
            app_commands.Command(
                name="shake",
                description="'shake' a user in voice as a fruitless attempt to get their attention.",
                callback=self.vcShake,
            )
        )
        self.bot.voiceCommandsGroup.add_command(
            app_commands.Command(
                name="disconnect",
                description="Disconnect yourself from the voice channel you're in.",
                callback=self.vc_disconnect,
            )
        )
        self.bot.voiceCommandsGroup.add_command(
            app_commands.Command(
                name="move_me",
                description="Move you to another channel",
                callback=self.vc_move,
            )
        )

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.stealEmojiMenu.name, type=self.stealEmojiMenu.type)
        self.bot.tree.remove_command(self.videoLengthMenu.name, type=self.videoLengthMenu.type)
        self.bot.voiceCommandsGroup.remove_command("shake")
        self.bot.voiceCommandsGroup.remove_command("disconnect")
        self.bot.voiceCommandsGroup.remove_command("move_me")

    async def videoLength(self, interaction: discord.Interaction, message: discord.Message):
        matches = YOUTUBE_REGEX.findall(message.content)
        if len(matches) == 0:
            await interaction.response.send_message("there's no youtube link in this message :(", ephemeral=True)
            return
        lengths = {}
        for match in matches:
            async with aiohttp.ClientSession() as session:
                data = await get_json(
                    session,
                    f"https://www.googleapis.com/youtube/v3/videos?part=contentDetails&id={matches[0]}&key={self.bot.config.youtube_token}",
                )
                if len(data["items"]) == 0:
                    await interaction.response.send_message("that's not a valid youtube link :(", ephemeral=True)
                    return
                duration = data["items"][0]["contentDetails"]["duration"]
                duration = duration[2:]  # remove the "PT" prefix
                days = 0
                hours = 0
                minutes = 0
                seconds = 0
                if "D" in duration:
                    parts = duration.split("D")
                    days = int(parts[0])
                    duration = parts[1]
                if "H" in duration:
                    parts = duration.split("H")
                    hours = int(parts[0])
                    duration = parts[1]
                if "M" in duration:
                    parts = duration.split("M")
                    minutes = int(parts[0])
                    duration = parts[1]
                if "S" in duration:
                    parts = duration.split("S")
                    seconds = int(parts[0])
                duration_string = f"{days}{' days, ' if days > 0 else ''}{hours:02d}:{minutes:02d}:{seconds:02d}"
                lengths[match] = duration_string
        await interaction.response.send_message(
            f"{' and '.join([f'{link} is {length}' for link, length in lengths.items()])}", ephemeral=True
        )

    async def stealEmoji(self, interaction: discord.Interaction, message: discord.Message):
        raw_emojis = self.EMOJI_REGEX.findall(message.content)
        raw_emojis += self.FALLBACK_EMOJI_REGEX.findall(message.content)
        emojis = [
            PartialEmoji.with_state(self.bot._connection, animated=(e[0] == 'a'), name=e[1], id=e[2])
            for e in raw_emojis
        ]
        if len(emojis) == 0:
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
                    f"{'these' if len(uploads) > 1 else 'this'} is mine now\n\n{' '.join(uploads)}"
                )

        class EmojiSelector(ui.View):
            def __init__(self):
                super().__init__(timeout=60)
                self.add_item(IndexSelector(message))

        await interaction.response.send_message(view=EmojiSelector(), ephemeral=True)

    async def vc_disconnect(self, interaction: discord.Interaction):
        """Disconnects you from voice"""
        if interaction.guild is None:
            await interaction.response.send_message("this command can only be used in a server", ephemeral=True)
            return
        if interaction.user.voice is None:
            await interaction.response.send_message("you're not in a voice channel", ephemeral=True)
            return
        if interaction.user.voice.channel is None:
            await interaction.response.send_message("you're not in a voice channel", ephemeral=True)
            return
        if interaction.user.voice.channel.guild != interaction.guild:
            await interaction.response.send_message("you're not in this server's voice channel", ephemeral=True)
            return
        await interaction.user.voice.channel.disconnect()
        await interaction.response.send_message("ok, bye", ephemeral=True)

    async def vc_move(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        """Moves you to another voice channel"""
        if interaction.guild is None:
            await interaction.response.send_message("this command can only be used in a server", ephemeral=True)
            return
        if not interaction.user.voice:
            await interaction.response.send_message("you're not in a voice channel", ephemeral=True)
            return
        if interaction.user.voice.channel is None:
            await interaction.response.send_message("you're not in a voice channel", ephemeral=True)
            return
        if interaction.user.voice.channel.guild != interaction.guild:
            await interaction.response.send_message("you're not in this server's voice channel", ephemeral=True)
            return
        if channel.permissions_for(interaction.user).connect is False:
            await interaction.response.send_message(
                "you don't have permission to connect to that channel", ephemeral=True
            )
            return
        await interaction.user.move_to(channel)
        await interaction.response.send_message("ok, bye", ephemeral=True)

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

    async def target_autocomplete(self, interaction: discord.Interaction, guess: str) -> List[app_commands.Choice]:
        if interaction.user.voice is None:
            return [app_commands.Choice(name="err: not in a voice channel", value="0")]
        if interaction.guild.afk_channel is None:
            return [app_commands.Choice(name="err: no afk channel", value="0")]
        if interaction.user.voice.channel == interaction.guild.afk_channel:
            return [app_commands.Choice(name="err: in afk channel", value="0")]

        valid_targets = [
            m
            for m in interaction.user.voice.channel.members
            if not m.bot and not m.id == interaction.user.id and not m.voice.self_stream
        ]
        if len(valid_targets) == 0:
            return [app_commands.Choice(name="err: no valid targets", value="0")]
        return [
            app_commands.Choice(name=m.display_name, value=str(m.id))
            for m in valid_targets
            if guess in m.display_name.lower() or guess in m.name.lower()
        ]

    @app_commands.guild_only()
    @app_commands.autocomplete(target=target_autocomplete)
    async def vcShake(self, interaction: discord.Interaction, target: str):
        """'shake' a user in voice as a fruitless attempt to get their attention."""
        target: int = int(target)
        if not interaction.guild.me.guild_permissions.move_members:
            await interaction.response.send_message("I don't have the permissions to do that.")
            return

        if target == 0:
            await interaction.response.send_message("invalid target", ephemeral=True)
            return

        if interaction.user.voice is None:
            await interaction.response.send_message("you are not in a voice channel", ephemeral=True)
            return
        if interaction.guild.afk_channel is None:
            await interaction.response.send_message("there is no afk channel", ephemeral=True)
            return

        if interaction.user.voice.channel == interaction.guild.afk_channel:
            await interaction.response.send_message("you are in the afk channel", ephemeral=True)
            return

        valid_targets = [
            m
            for m in interaction.user.voice.channel.members
            if not m.bot and not m.id == interaction.user.id and not m.voice.self_stream
        ]

        user = interaction.guild.get_member(int(target))
        if user is None or user not in valid_targets:
            await interaction.response.send_message("invalid target", ephemeral=True)
            return

        currentChannel = interaction.user.voice.channel
        AFKChannel = interaction.guild.afk_channel

        await interaction.response.send_message(
            f"shaking {user.mention}...",
            allowed_mentions=discord.AllowedMentions.none(),
        )
        voiceLog = self.bot.get_cog("VoiceLog")
        if voiceLog:
            voiceLog.beingShaken[user.id] = False
        if interaction.guild.id == 791528974442299412:
            await interaction.guild.get_channel(974472799093661826).send(
                f"shaking {user.display_name} for {interaction.user.display_name}"
            )

        for _ in range(4):
            await user.move_to(AFKChannel, reason=f"shake requested by {interaction.user.display_name}")
            await user.move_to(currentChannel, reason=f"shake requested by {interaction.user.display_name}")
        if voiceLog:
            del voiceLog.beingShaken[user.id]

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if self.bot.location == "dev" or message.guild is None:
            return

        if message.guild.id == 791528974442299412 and message.channel.category_id != 822958326249816095:
            if any(
                [banned_phrase in message.content.lower() for banned_phrase in self.bot.config.nerdiowoBannedPhrases]
            ):
                await message.delete()
                await message.channel.send("BAD WORD DETECTED. MESSAGE DESTROYED.", delete_after=5)
                return
        cfg = (await self.bot.db.get_guild_data(message.guild.id)).config
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
                        pass

                return
            else:
                try:
                    await message.author.send(
                        f"Your message was deleted. please end it with a `?`\n\nYour original content is here:"
                    )
                    await message.author.send(message.content)
                except discord.DiscordException:
                    pass

                await message.delete()
        if (
            message.guild
            and message.guild.id == 791528974442299412
            and any(word in message.content.lower() for word in ARSON_STRING)
        ):
            await message.reply("arson", mention_author=False)


async def setup(bot):
    await bot.add_cog(Fun(bot))
