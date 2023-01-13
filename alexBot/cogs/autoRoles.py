import asyncio
from typing import Dict, List, Optional

import discord
from discord import app_commands

from alexBot.classes import ButtonRole, ButtonType
from alexBot.tools import Cog


def make_callback(btnRole: ButtonRole, otherRoles: List[ButtonRole]):
    """
    if otherRoles is set, it will remove all other roles in the list from the user
    """

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


ALLOWMANYROLES = {
    ButtonType.LOCATION: False,
    ButtonType.GAME: True,
    ButtonType.PHONE: True,
}


class autoRoles(Cog):
    roles: Dict[ButtonType, List[ButtonRole]] = {}
    views: Dict[ButtonType, discord.ui.View] = {}

    async def cog_load(self):
        self.views = {
            ButtonType.LOCATION: discord.ui.View(timeout=None),
            ButtonType.GAME: discord.ui.View(timeout=None),
            ButtonType.PHONE: discord.ui.View(timeout=None),
        }
        roles = await self.bot.db.get_roles_data()
        for type in ButtonType:
            self.roles[type] = [r for r in roles if r.type == type]

        for type in ButtonType:
            for role in self.roles[type]:
                btn = discord.ui.Button(
                    label=role.label, emoji=role.emoji, custom_id=f"nerdiowo-roleRequest-{role.role}"
                )

                btn.callback = make_callback(role, self.roles[type] if ALLOWMANYROLES[type] else [])

                self.views[type].add_item(btn)
            self.bot.add_view(self.views[type], message_id=self.roles[type][0].message)

    nerdiowo_roles = app_commands.Group(
        name="nerdiowo-roles", description="nerdiowo roles menu",
        guild_ids=[791528974442299412],
        default_permissions=discord.Permissions(manage_roles=True),
    )

    @nerdiowo_roles.command(name="add-new-role", description="add a new role to the role request menu")
    async def role_create(
        self,
        interaction: discord.Interaction,
        btntype: ButtonType,
        role: discord.Role,
        label: str,
        emoji: Optional[str],
    ):
        try:
            v = discord.ui.View()
            v.add_item(discord.ui.Button(label=label, emoji=emoji))
            await interaction.response.send_message(view=v, ephemeral=True)
        except discord.HTTPException:
            await interaction.response.send_message("invalid emoji", ephemeral=True)
            return
        mid = self.roles[btntype][0].message
        self.roles[btntype].append(ButtonRole(label, role.id, mid, btntype, str(emoji) if emoji else None))
        roles = []
        for type in self.roles:
            roles.extend(self.roles[type])
        await self.bot.db.save_roles_data(roles)
        await self.cog_load()
        await (await (self.bot.get_channel(791528974442299415).fetch_message(mid))).edit(view=self.views[btntype])
        await interaction.followup.send("added role")

    @nerdiowo_roles.command(name="remove-role", description="remove a role from the role request menu")
    async def role_remove(self, interaction: discord.Interaction, btntype: ButtonType, role: discord.Role):
        self.roles[btntype] = [r for r in self.roles[btntype] if r.role != role.id]
        roles = []
        for type in self.roles:
            roles.extend(self.roles[type])
        await self.bot.db.save_roles_data(roles)
        await self.cog_load()
        await (await (self.bot.get_channel(791528974442299415).fetch_message(self.roles[btntype][0].message))).edit(
            view=self.views[btntype]
        )
        await interaction.followup.send("removed role")


async def setup(bot):
    await bot.add_cog(autoRoles(bot))
