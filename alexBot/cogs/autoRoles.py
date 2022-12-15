import discord
from discord.ext import commands
from alexBot.classes import ButtonRole

from alexBot.tools import Cog


def make_callback(btnRole: ButtonRole):
    async def callback(interaction: discord.Interaction):
        assert isinstance(interaction.user, discord.Member)
        assert isinstance(interaction.guild, discord.Guild)

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
        self.rolesView = discord.ui.View(timeout=None)
        for btnRole in self.bot.config.nerdiowoRoles:
            btn = discord.ui.Button(label=btnRole.label, emoji=btnRole.emoji, custom_id=f"nerdiowo-roleRequest-{btnRole.role}")
            btn.callback = make_callback(btnRole)

            self.rolesView.add_item(btn)

        if self.bot.config.nerdiowoRolesMessageId:
            self.bot.add_view(self.rolesView, message_id=self.bot.config.nerdiowoRolesMessageId)

    @commands.is_owner()
    @commands.command()
    async def roles(self, ctx: commands.Context):
        await ctx.send("click the buttons to add/remove roles", view=self.rolesView)

    @commands.is_owner()
    @commands.command()
    async def updateRolesMessage(self, ctx: commands.Context, channel: discord.TextChannel):
        await (await channel.fetch_message(self.bot.config.nerdiowoRolesMessageId)).edit(view=self.rolesView)
        await ctx.send("done")

async def setup(bot):
    await bot.add_cog(autoRoles(bot))
