import logging
import re
import time
from typing import Dict

import discord
from discord import MessageType, PartialEmoji
from discord.ext import commands
from emoji_data import EmojiSequence

from ..tools import Cog, get_json

log = logging.getLogger(__name__)
ayygen = re.compile("[aA][yY][Yy][yY]*")

VOTE_EMOJIS = ["<:greentick:567088336166977536>", "<:yellowtick:872631240010899476>", "<:redtick:567088349484023818>"]


class Fun(Cog):
    last_posted: Dict[int, float] = {}

    EMOJI_REGEX = re.compile(r"<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>")

    @commands.command(aliases=["emojiSteal"])
    @commands.is_owner()
    async def stealEmoji(self, ctx: commands.Context, index: int = 0):
        if not ctx.message.reference:
            raise commands.BadArgument("you need to reply to a message")
        target = ctx.message.reference.resolved
        raw_emojis = self.EMOJI_REGEX.findall(target.content)
        emojis = [
            PartialEmoji.with_state(self.bot._connection, animated=(e[0] == 'a'), name=e[1], id=e[2])
            for e in raw_emojis
        ]

        emoji = emojis[index]
        data = await emoji.url.read()
        nerdiowo = ctx.bot.get_guild(791528974442299412)
        uploaded = await nerdiowo.create_custom_emoji(name=emoji.name, image=data)
        try:
            await ctx.reply(f"{uploaded}")
        except discord.errors.Forbidden:
            await ctx.author.send(f"{uploaded}")

    @commands.command()
    async def cat(self, ctx: commands.Context):
        """Posts a pretty photo of a cat"""
        cat = await get_json(
            self.bot.session,
            f"https://thecatapi.com/api/images/get?format=json" f"&api_key={self.bot.config.cat_token}",
        )
        cat = cat[0]
        embed = discord.Embed()
        embed.set_image(url=cat["url"])
        embed.url = "http://thecatapi.com"
        embed.title = "cat provided by the cat API"
        await ctx.send(embed=embed)

    @commands.command()
    async def dog(self, ctx: commands.Context):
        """Posts a pretty picture of a dog."""
        dog = None
        while dog is None or dog["url"][-3:].lower() == "mp4":
            dog = await get_json(self.bot.session, "https://random.dog/woof.json")
            log.debug(dog["url"])
        ret = discord.Embed()
        ret.set_image(url=dog["url"])
        await ctx.send(embed=ret)

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
                            data = await emoji.url.read()
                            nerdiowo = self.bot.get_guild(791528974442299412)
                            uploaded = await nerdiowo.create_custom_emoji(
                                name=emoji.name, image=data, reason="temporily added for #everybody-votes"
                            )
                            await message.add_reaction(uploaded)
                            await uploaded.delete(reason="removed from temp addition")
                        pass

                return
            elif message.type == MessageType.thread_created:
                return
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
