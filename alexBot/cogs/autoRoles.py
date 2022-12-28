import asyncio
from typing import List

import discord
from discord.ext import commands

from alexBot.classes import ButtonRole
from alexBot.tools import Cog


def make_callback(btnRole: ButtonRole, otherRoles: List[ButtonRole]):
    async def callback(interaction: discord.Interaction):
        assert isinstance(interaction.user, discord.Member)
        assert isinstance(interaction.guild, discord.Guild)

        roles = [interaction.guild.get_role(role.role) for role in otherRoles if role.role != btnRole.role]
        if any([role.id in [r.id for r in interaction.user.roles] for role in roles]):
            asyncio.get_event_loop().create_task(interaction.user.remove_roles(*roles))

        if interaction.user.get_role(btnRole.role):
            await interaction.user.remove_roles(interaction.guild.get_role(btnRole.role))
            await interaction.response.send_message(f"removed the {btnRole.label} role for you!", ephemeral=True)
        else:
            await interaction.user.add_roles(interaction.guild.get_role(btnRole.role))
            await interaction.response.send_message(f"added the {btnRole.label} role for you!", ephemeral=True)

    return callback


class autoRoles(Cog):
    def __init__(self, bot):
        super().__init__(bot)
        self.locationRolesView = discord.ui.View(timeout=None)
        for btnRole in self.bot.config.nerdiowoLocationRoles:
            btn = discord.ui.Button(
                label=btnRole.label, emoji=btnRole.emoji, custom_id=f"nerdiowo-roleRequest-{btnRole.role}"
            )

            btn.callback = make_callback(btnRole, self.bot.config.nerdiowoLocationRoles)

            self.locationRolesView.add_item(btn)

        self.gameRolesView = discord.ui.View(timeout=None)
        for btnRole in self.bot.config.nerdiowoGamesRoles:
            btn = discord.ui.Button(
                label=btnRole.label, emoji=btnRole.emoji, custom_id=f"nerdiowo-roleRequest-{btnRole.role}"
            )

            btn.callback = make_callback(btnRole, [])

            self.gameRolesView.add_item(btn)

        self.phoneRolesView = discord.ui.View(timeout=None)
        for btnRole in self.bot.config.nerdiowoPhonesRoles:
            btn = discord.ui.Button(
                label=btnRole.label, emoji=btnRole.emoji, custom_id=f"nerdiowo-roleRequest-{btnRole.role}"
            )

            btn.callback = make_callback(btnRole, [])

            self.phoneRolesView.add_item(btn)

        if self.bot.config.nerdiowoLocationRolesMessageId:
            self.bot.add_view(self.locationRolesView, message_id=self.bot.config.nerdiowoLocationRolesMessageId)

        if self.bot.config.nerdiowoGamesRolesMessageId:
            self.bot.add_view(self.gameRolesView, message_id=self.bot.config.nerdiowoGamesRolesMessageId)

        if self.bot.config.nerdiowoPhonesRolesMessageId:
            self.bot.add_view(self.phoneRolesView, message_id=self.bot.config.nerdiowoPhonesRolesMessageId)

    @commands.is_owner()
    @commands.command()
    async def postLocationRolesButtons(self, ctx: commands.Context):
        self.bot.config.nerdiowoLocationRolesMessageId = (
            await ctx.send("click the buttons to add/remove roles", view=self.locationRolesView)
        ).id

    @commands.is_owner()
    @commands.command()
    async def updateLocationRolesMessage(self, ctx: commands.Context, channel: discord.TextChannel):
        await (await channel.fetch_message(self.bot.config.nerdiowoLocationRolesMessageId)).edit(
            view=self.locationRolesView
        )
        await ctx.send("done")

    @commands.is_owner()
    @commands.command()
    async def postGamesButtons(self, ctx: commands.Context):
        self.bot.config.nerdiowoGamesRolesMessageId = (
            await ctx.send("click the buttons to add/remove roles", view=self.gameRolesView)
        ).id

    @commands.is_owner()
    @commands.command()
    async def updateGamesRolesMessage(self, ctx: commands.Context, channel: discord.TextChannel):
        await (await channel.fetch_message(self.bot.config.nerdiowoGamesRolesMessageId)).edit(view=self.gameRolesView)
        await ctx.send("done")

    @commands.is_owner()
    @commands.command()
    async def postPhoneButtons(self, ctx: commands.Context):
        self.bot.config.nerdiowoPhonesRolesMessageId = (
            await ctx.send("click the buttons to add/remove roles", view=self.gameRolesView)
        ).id

    @commands.is_owner()
    @commands.command()
    async def updatePhoneRolesMessage(self, ctx: commands.Context, channel: discord.TextChannel):
        await (await channel.fetch_message(self.bot.config.nerdiowoPhonesRolesMessageId)).edit(view=self.gameRolesView)
        await ctx.send("done")


async def setup(bot):
    await bot.add_cog(autoRoles(bot))
