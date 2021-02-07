from typing import Awaitable, Dict, List

import discord

from ..tools import Cog


class ReactionMenu:
    message: discord.Message = None
    actions: Dict[discord.Emoji, Awaitable] = {}

    async def on_reaction_added(reaction: discord.Reaction):
        pass

    async def on_reaction_removed(reacton: discord.Reaction):
        pass


class ReactionMenuHandler(Cog):
    activeMenus: List[ReactionMenu] = []

    @Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.Member):
        """handels reactions, only for active menus."""
        # get the reactionMenu from the activeMenus

        # see if the reaction has meaning, and then do that meaning (typicly execute function on the reactMenu)

    async def on_reaction_menu_remote(self, reactionMenu: ReactionMenu):
        """will allow a reactionMenu to be ended, typicly by deleting embed and replacing with a text menssage"""

        # get ReactionMenu from activeMenu
        # remove it from discord's side w/ message.edit
        # remove it from activeMenus list


def setup(bot):
    bot.add_cog(ReactionMenuHandler(bot))
