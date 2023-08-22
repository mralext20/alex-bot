from typing import Literal

import discord
from discord import app_commands
from discord.ext.commands.errors import BadBoolArgument
from sqlalchemy import select

from alexBot.classes import googleVoices
from alexBot.database import GuildConfig, UserConfig, async_session

from ..tools import Cog, convert_to_bool


class Configs(Cog):
    """handles config settings"""

    configCommandGroup = app_commands.Group(
        name="config", description="Guild and User config commands", guild_only=True
    )
    configGuildCommandGroup = app_commands.Group(
        name="guild", parent=configCommandGroup, description="Guild config commands", guild_only=True
    )
    configUserCommandGroup = app_commands.Group(
        name="user", parent=configCommandGroup, description="User config commands", guild_only=True
    )

    @configUserCommandGroup.command(name="show", description="shows the current config")
    async def user_showConfig(self, interaction: discord.Interaction):
        async with async_session() as session:
            config = await session.scalar(select(UserConfig).where(UserConfig.userId == interaction.user.id))
            if not config:
                config = UserConfig(userId=interaction.user.id)
                session.add(config)
                await session.commit()
            embed = discord.Embed()
            embed.title = f"User Config for {interaction.user.name}"
            embed.set_author(
                name=interaction.user.display_name,
                icon_url=interaction.user.avatar.url if interaction.user.avatar else None,
            )
            for key in config.__config_keys__:
                embed.add_field(name=key, value=getattr(config, key))
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @configUserCommandGroup.command(name="set", description="sets a config value")
    @app_commands.choices(key=[app_commands.Choice(name=key, value=key) for key in UserConfig.__config_keys__])
    async def user_setConfig(self, interaction: discord.Interaction, key: str, value: str):
        # it's a user! we don't need to confirm they can set the key.
        if key == 'voiceModel':
            vcnames = [vc[0] for vc in googleVoices]
            if value not in vcnames:
                formatted = '\n'.join([f'`{vc[0]}` ({vc[1]})' for vc in googleVoices])
                await interaction.response.send_message(
                    f"{value} is not a valid voice model. valid models are: \n\n{formatted}",
                    ephemeral=True,
                )
                return
        await self.setConfig('user', interaction, key, value)

    async def setConfig(
        self, config_type: Literal['guild', 'user'], interaction: discord.Interaction, key: str, value: str
    ):
        # set locals
        model = None
        lookUpID = None
        if config_type == 'guild':
            model = GuildConfig
            lookUpID = interaction.guild.id
        elif config_type == 'user':
            model = UserConfig
            lookUpID = interaction.user.id
        else:
            raise ValueError("config_type must be 'guild' or 'user'")
        if key not in model.__config_keys__:
            await interaction.response.send_message("That is not a valid config key!", ephemeral=True)
            return
        type = model.__dataclass_fields__[key].type
        # attempt to cast input value to type
        if type == bool:
            try:
                val = convert_to_bool(value)
            except BadBoolArgument:
                await interaction.response.send_message("That is not a valid bool value!", ephemeral=True)
                return
        else:
            val = value
        # get the user config
        async with async_session() as session:
            uc = await session.scalar(select(model).where(model.__mapper__.primary_key[0] == lookUpID))
            if not uc:
                uc = model(lookUpID)
            setattr(uc, key, val)
            session.add(uc)
            await session.commit()
        await interaction.response.send_message(
            f"Set {key} to {val}", ephemeral=True if config_type == 'guild' else False
        )

    @configGuildCommandGroup.command(name="show", description="shows the current config")
    async def guild_showConfig(self, interaction: discord.Interaction):
        async with async_session() as session:
            config = await session.scalar(select(GuildConfig).where(GuildConfig.guildId == interaction.guild.id))
            if not config:
                config = GuildConfig(guildId=interaction.guild.id)
                session.add(config)
                await session.commit()
            embed = discord.Embed()
            embed.title = f"Guild Config for {interaction.guild.name}"
            embed.set_author(
                name=interaction.guild.name, icon_url=interaction.guild.icon.url if interaction.guild.icon else None
            )
            for key in config.__config_keys__:
                embed.add_field(name=key, value=getattr(config, key))
            await interaction.response.send_message(embed=embed, ephemeral=False)

    @configGuildCommandGroup.command(name="set", description="sets a config value")
    @app_commands.choices(key=[app_commands.Choice(name=key, value=key) for key in GuildConfig.__config_keys__])
    async def guild_setConfig(self, interaction: discord.Interaction, key: str, value: str):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "You don't have permission to do that! (need Manage Guild)", ephemeral=True
            )
            return
        # from here it's identical to user_setConfig, so we call into set_config
        await self.setConfig('guild', interaction, key, value)


async def setup(bot):
    await bot.add_cog(Configs(bot))
