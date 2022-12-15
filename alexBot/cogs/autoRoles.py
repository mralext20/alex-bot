import discord
from discord.ext import commands

from alexBot.tools import Cog


class autoRoles(Cog):
    def __init__(self, bot: "Bot"):
        super().__init__(bot)
        self.rolesView = discord.ui.View(timeout=None)
        for name, roleId in self.bot.config.nerdiowoRoles.items():
            btn = discord.ui.Button(label=name, custom_id=f"nerdiowo-roleRequest-{roleId}")

            async def callback(interaction: discord.Interaction):
                assert isinstance(interaction.user, discord.Member)
                assert isinstance(interaction.guild, discord.Guild)

                if interaction.user.get_role(roleId):
                    await interaction.user.remove_roles(interaction.guild.get_role(roleId))
                    await interaction.response.send_message(f"removed the {name} role for you!", ephemeral=True)
                else:
                    await interaction.user.add_roles(interaction.guild.get_role(roleId))
                    await interaction.response.send_message(f"added the {name} role for you!", ephemeral=True)
            btn.callback = callback

            self.rolesView.add_item(btn)

        if self.bot.config.nerdiowoRolesMessageId:
            self.bot.add_view(self.rolesView, message_id=self.bot.config.nerdiowoRolesMessageId)


    @commands.is_owner()
    @commands.command()
    async def roles(self, ctx: commands.Context):
        await ctx.send("click the buttons to add/remove roles", view=self.rolesView)


async def setup(bot):
    await bot.add_cog(autoRoles(bot))
