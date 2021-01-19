from dataclasses import dataclass
from ..tools import Cog
import discord
from discord.ext import commands
from typing import List
import asyncio
import logging


log = logging.getLogger(__name__)


def debugger():
    pass


@dataclass
class ReactionRole:
    guildId: int
    messageid: int
    reaction: str
    roleId: int

    @classmethod
    def from_row(cls, row):
        return cls(row[0], row[1], row[2], row[3])


class ReactionRoles(Cog):
    def __init__(self, bot):
        super().__init__(bot)
        self.messageTargets: List[id] = []
        asyncio.create_task(self.update_message_targets())

    async def update_message_targets(self):
        res = await self.bot.db.execute("""SELECT messageId from reactionRoles""")
        [self.messageTargets.append(row[0]) for row in (await res.fetchall())]

    async def add_reaction_role(self, message: discord.Message, reaction: str, role: discord.Role):
        try:
            await message.add_reaction(reaction)
        except (discord.Forbidden, discord.NotFound, discord.InvalidArgument):
            raise commands.BadArgument("Your emoji isn't an emoji or i cant add emoji in that channel")
        newEmbed = message.embeds[0]
        newEmbed.description = f"{newEmbed.description}\n{reaction}: {role.mention}"
        await message.edit(embed=message.embeds[0])
        await self.bot.db.execute(
            """INSERT INTO reactionRoles (guildId, messageId, reaction, roleId) VALUES (?,?,?,?)""",
            (message.guild.id, message.id, reaction, role.id),
        )
        self.messageTargets.append(message.id)
        await self.bot.db.commit()

    async def remove_reaction_role(self, role: discord.Role):
        await self.bot.db.execute("""DELETE FROM reactionRoles WHERE roleId=?""", (role.id,))
        await self.bot.db.commit()

    @Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.message_id not in self.messageTargets or payload.member == self.bot.user:
            return
        log.debug("recived reaction: {payload}")
        row = await self.bot.db.execute(
            """SELECT * FROM reactionRoles WHERE messageId=? AND reaction=?""", (payload.message_id, payload.emoji.name)
        )
        data = ReactionRole.from_row(await row.fetchone())
        log.debug(data)
        payload.member.add_roles()

    @commands.command()
    @commands.has_guild_permissions(manage_guild=True)
    async def setup_reaction_role(
        self, ctx: commands.Context, channel: discord.TextChannel, role: discord.Role, reaction: str
    ):
        try:
            self.bot.get_channel
            assert channel.guild == ctx.guild
        except AssertionError:
            raise commands.BadArgument("channel needs to be in this server")
            # find existing message in channel OR create message in channel
        message: discord.Message = None
        async for msg in channel.history():
            if msg.author == self.bot.user and msg.id in self.messageTargets:
                message = msg
                break
        else:
            embed = discord.Embed()
            embed.description = "React to get a Role:\n"
            message = await channel.send(embed=embed)
            self.messageTargets.append(message.id)
        await self.add_reaction_role(message, reaction, role)
        await ctx.message.add_reaction("✅")


# def setup(bot):
#     bot.add_cog(ReactionRoles(bot))
