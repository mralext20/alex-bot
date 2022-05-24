import dataclasses
from datetime import timezone
from typing import Callable, Dict, TypeVar

import discord
import pytz
from discord.ext import commands

from alexBot.classes import GuildConfig, UserData

from ..tools import Cog

_T = TypeVar("_T")

typeMap: Dict[_T, Callable[[str], _T]] = {
    bool: lambda s: s[0].lower() in ['y', 't'],
    str: lambda s: s,
    timezone: pytz.timezone,
}


class Configs(Cog):
    """handles guild config settings"""

    @commands.group(name="config", invoke_without_command=True)
    async def config(self, ctx: commands.Context):
        """how you configure your self, or the server if you have that permissions."""
        embed = discord.Embed(title="Config")
        if ctx.author.guild_permissions.manage_guild:
            gdc = dataclasses.asdict((await self.bot.db.get_guild_data(ctx.guild.id)).config)
            for key in gdc:
                if isinstance(gdc[key], list):
                    continue
                embed.add_field(name=f"guild.{key}", value=gdc[key] if gdc[key] else "*unset*")

        uc = dataclasses.asdict((await self.bot.db.get_user_data(ctx.author.id)).config)
        [embed.add_field(name=f"user.{name}", value=uc[name]) for name in uc]
        embed.set_footer(text=f"to set a field, use {self.bot.command_prefix}config set <key> <value>")
        await ctx.send(embed=embed)

    @config.command(name="set")
    async def config_set(self, ctx: commands.Context, rawkey: str, *, rawvalue: str):
        typekey, key = rawkey.split('.')
        if typekey == "guild":
            if not ctx.author.guild_permissions.manage_guild:
                raise commands.errors.MissingPermissions([discord.Permissions(manage_guild=True)])
            gd = await self.bot.db.get_guild_data(ctx.guild.id)
            if isinstance(getattr(gd.config, key, list()), list):
                raise commands.errors.BadArgument(f"cannot set that key {key}")
            if (t := type(getattr(gd.config, key))) in typeMap:
                value = typeMap[t](rawvalue)
            else:
                raise commands.errors.BadArgument(f"cannot set that key {key}")
            setattr(gd.config, key, value)
            await self.bot.db.save_guild_data(ctx.guild.id, gd)
            await ctx.send(f"successfully set {typekey}.{key} to {value}")
            return
        elif typekey == "user":
            ud = await self.bot.db.get_user_data(ctx.author.id)
            if isinstance(getattr(ud.config, key, list()), list):
                raise commands.errors.BadArgument(f"cannot set that key {key}")
            if (t := type(getattr(ud.config, key))) in typeMap:
                value = typeMap[t](rawvalue)
            else:
                raise commands.errors.BadArgument(f"cannot set that key {key}")
            setattr(ud.config, key, value)
            await self.bot.db.save_user_data(ctx.author.id, ud)
            await ctx.send(f"successfully set {typekey}.{key} to {value}")
            return
        else:
            raise commands.errors.BadArgument(
                f"the typekey {typekey} does not exist. please check `{self.bot.command_prefix}config` for a list of keys."
            )

    @config.command(name="reset")
    async def config_reset(self, ctx: commands.Context, rawkey: str):
        keys = rawkey.split('.')
        try:
            typekey, key = keys
        except ValueError:
            raise commands.errors.BadArgument("your key is not valid")
        if typekey == "guild":
            if not ctx.author.guild_permissions.manage_guild:
                raise commands.errors.MissingPermissions([discord.Permissions(manage_guild=True)])
            defaultGDC = GuildConfig()
            default = getattr(defaultGDC, key, None)
            if default is None:
                raise commands.BadArgument(f"The key {key} is not a valid key on {typekey}")
            currGD = await self.bot.db.get_guild_data(ctx.guild.id)
            setattr(currGD.config, key, default)  # currGD.config.$KEY = default
            await self.bot.db.save_guild_data(currGD)
            await ctx.send(f"set {typekey}.{key} to {default}, the default value.")

        elif typekey == "user":
            defaultUD = UserData()
            default = getattr(defaultUD.config, key, None)  # default = defaultUD.config.$KEY or None
            if default is None:
                raise commands.BadArgument(f"The key {key} is not a valid key on {typekey}")
            ud = await self.bot.db.get_user_data(ctx.author.id)
            setattr(ud.config, key, default)  # ud.config.$KEY = defualt
            await self.bot.db.save_user_data(ctx.author.id, ud)
            await ctx.send(f"set {typekey}.{key} to {default}, the default value.")
        else:
            raise commands.errors.BadArgument(
                f"{typekey} is not a valid typekey. see `{self.bot.command_prefix}config` for a list of valid keys."
            )


async def setup(bot):
    await bot.add_cog(Configs(bot))
