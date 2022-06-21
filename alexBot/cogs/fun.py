import logging
import re
import time
from typing import Dict
import aiohttp

import discord
from discord import MessageType, PartialEmoji, app_commands, ui
from discord.ext import commands
from emoji_data import EmojiSequence

from ..tools import Cog, get_json

log = logging.getLogger(__name__)
ayygen = re.compile("[aA][yY][Yy][yY]*")

VOTE_EMOJIS = ["<:greentick:567088336166977536>", "<:yellowtick:872631240010899476>", "<:redtick:567088349484023818>"]





class Fun(Cog):
    def __init__(self, bot: "Bot"):
        super().__init__(bot)
        self.last_posted: Dict[int,float] = {}
        self.stealEmojiMenu = app_commands.ContextMenu(
            name='Steal Emojis',
            callback=self.stealEmoji,
        )
        self.EMOJI_REGEX = re.compile(r"<a?:[a-zA-Z0-9_]{2,32}:[0-9]{18,22}>")
        self.bot.tree.add_command(self.stealEmojiMenu, guild=discord.Object(791528974442299412))

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.stealEmojiMenu.name, type=self.stealEmojiMenu.type)


    async def stealEmoji(self, interaction: discord.Interaction, message: discord.Message):
        raw_emojis = self.EMOJI_REGEX.findall(message.content)
        emojis = [
            PartialEmoji.from_str(e)
            for e in raw_emojis
        ]
        bot = self.bot

        class IndexSelector(ui.Modal, title="Which emoji?"):
            index = ui.Select(max_values=25, options=[discord.SelectOption(label=e.name, value=str(index), emoji=e) for index, e in enumerate(emojis)])

            async def on_submit(self, interaction: discord.Interaction):
                await interaction.response.send_message("i'll get right on that!", ephemeral=True)
                
                nerdiowo = bot.get_guild(791528974442299412)
                for i in self.index.values:
                    index = int(i)
                    emoji = emojis[index]
                    data = await emoji.read()
                    uploaded = await nerdiowo.create_custom_emoji(name=emoji.name, image=data)
                    await interaction.followup.send(f"{uploaded}", ephemeral=True)

        await interaction.response.send_modal(IndexSelector())


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
        if self.bot.location == "dev" or message.guild is None:
            return
        cfg = (await self.bot.db.get_guild_data(message.guild.id)).config
        if cfg.ayy:
            if ayygen.fullmatch(message.content):
                await message.reply("lmao", mention_author=False)
        if cfg.veryCool:
            if message.content.lower().startswith("thank you "):
                await message.reply("very cool", mention_author=False)
        if cfg.firstAmendment:
            if any([check in message.content.lower() for check in ["free speech", "first amendment"]]):
                if self.last_posted.get(message.channel.id, time.time() - 60 * 60 * 24) < time.time() - 60 * 5:
                    await message.reply("https://xkcd.com/1357/", mention_author=True)
                    self.last_posted[message.channel.id] = time.time()

        # bespoke thing, maybe make config and guild based in the future
        if message.channel.id == 847555306166943755:
            if message.content.endswith('??'):
                # don't do anything, question is intending a thread
                return
            emojis = VOTE_EMOJIS
            raw_emojis = EmojiSequence.pattern.findall(message.content)
            matches = self.EMOJI_REGEX.findall(message.content)
            if matches or raw_emojis:
                emojis = [
                    PartialEmoji.from_str(e)
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
            elif message.type == MessageType.thread_created:
                await message.delete()  # thread creation messages delete without sending a message
            else:
                try:
                    await message.author.send(
                        f"Your message was deleted. please end it with a `?`\n\nYour original content is here:`{message.content}`"
                    )
                except discord.DiscordException:
                    pass

                await message.delete()


async def setup(bot):
    await bot.add_cog(Fun(bot))
