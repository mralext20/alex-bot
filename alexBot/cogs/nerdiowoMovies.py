# -*- coding: utf-8 -*-

import asyncio
import datetime
import enum
import logging
import random
from typing import List, Optional

import discord
import pytz
from discord.ext.commands import Paginator

from alexBot.classes import MovieSuggestion

from ..tools import Cog, InteractionPaginator

NERDIOWO_EVERYBODY_VOTES = 847555306166943755
NERDIOWO_MANAGE_SERVER_ID = 1046177820285603881
NERDIOWO_VOICE_CHANNEL = 1069499258115477525
NERDIOWO_ANNOUNCENENTS = 910725067003027547
NERDIOWO_MOVIE_NIGHT_ROLE = 1069492195415048192
NUMBER_EMOJIS = ["1️⃣", "2️⃣", "3️⃣"]

log = logging.getLogger(__name__)


class WatchedSelector(enum.Enum):
    ALL = enum.auto()
    WATCHED = enum.auto()
    UNWATCHED = enum.auto()


class NerdiowoMovies(Cog):
    def __init__(self, bot):
        super().__init__(bot)
        self.active_paginators: List[InteractionPaginator] = []

    async def autocomplete_unwatched_movie(
        self, interaction: discord.Interaction, movie_name: str
    ) -> List[discord.app_commands.Choice]:
        all_movies = await self.bot.db.get_movies_data()
        # only unwatched movies
        movies = [movie for movie in all_movies if not movie.watched]
        return [
            discord.app_commands.Choice(name=movie.title, value=movie.title)
            for movie in movies
            if movie_name.lower() in movie.title.lower()
        ]

    nerdiowo_movies = discord.app_commands.Group(
        name="movies",
        description="nerdiowo movies menu",
        guild_ids=[791528974442299412],
    )

    @nerdiowo_movies.command(name="list", description="list all movies")
    async def list_movies(
        self,
        interaction: discord.Interaction,
        watched_mode: Optional[WatchedSelector] = None,
    ):
        if watched_mode is None:
            watched_mode = WatchedSelector.ALL

        all_movies = await self.bot.db.get_movies_data()

        if watched_mode == WatchedSelector.WATCHED:
            movies = [movie for movie in all_movies if movie.watched]
        elif watched_mode == WatchedSelector.UNWATCHED:
            movies = [movie for movie in all_movies if not movie.watched]
        else:
            movies = all_movies

        paginator = Paginator(prefix="```", suffix="```", max_size=500)
        for movie in movies:
            paginator.add_line(
                f"{movie.title} - suggested by {interaction.guild.get_member(movie.suggestor)}{f' - watched on {movie.watchdate}' if movie.watched else ''}"
            )
        pi = InteractionPaginator(self.bot, paginator, owner=None)
        await pi.send_interaction(interaction)
        if watched_mode in [
            WatchedSelector.UNWATCHED,
            WatchedSelector.ALL,
        ]:  # only if new movies would need to be added to this paginator
            self.active_paginators.append(pi)
        while not pi.closed:
            await asyncio.sleep(5)
        del self.active_paginators[self.active_paginators.index(pi)]

    @nerdiowo_movies.command(name="suggest-new-movie", description="Suggest a new movie for the Nerdiowo Movie Night")
    async def suggest_new_movie(self, interaction: discord.Interaction, *, movie_name: str):
        all_movies = await self.bot.db.get_movies_data()
        # only unwatched movies
        movies = [movie for movie in all_movies if not movie.watched]
        submitters_movies = [movie for movie in movies if movie.suggestor == interaction.user.id]
        if len(submitters_movies) >= 3:
            await interaction.response.send_message(
                "You have already submitted 3 movies. You can only have 3 movies submitted at a time.",
                ephemeral=True,
            )
            return
        if movie_name in [movie.title for movie in movies]:
            await interaction.response.send_message("That movie has already been suggested", ephemeral=True)
            return
        suggestion = MovieSuggestion(title=movie_name, watched=False, suggestor=interaction.user.id, watchdate="")
        all_movies.append(suggestion)
        await self.bot.db.save_movies_data(all_movies)
        await interaction.response.send_message(f"Your movie suggestion, {suggestion.title} has been submitted.")
        for ip in self.active_paginators:
            await ip.add_line(
                f"{suggestion.title} - suggested by {interaction.guild.get_member(suggestion.suggestor)}{f' - watched on {suggestion.watchdate}' if suggestion.watched else ''}"
            )

    @nerdiowo_movies.command(name="remove-movie", description="Remove a movie from the list")
    async def remove_movie(self, interaction: discord.Interaction, movie_name: str):
        all_movies = await self.bot.db.get_movies_data()
        # only unwatched movies
        movies = [movie for movie in all_movies if not movie.watched]
        if not (
            interaction.user.guild_permissions.administrator or interaction.user.get_role(NERDIOWO_MANAGE_SERVER_ID)
        ):
            movies = [movie for movie in movies if movie.suggestor == interaction.user.id]
        if not movies:
            await interaction.response.send_message("You have not submitted any movies.", ephemeral=True)
            return
        try:
            movie = [movie for movie in movies if movie.title == movie_name][0]
        except IndexError:
            await interaction.response.send_message("That movie has not been suggested", ephemeral=True)
            return
        all_movies.remove(movie)
        await self.bot.db.save_movies_data(all_movies)
        await interaction.response.send_message(f"The movie suggestion, {movie.title} has been removed.")

    async def autocomplete_unwatched_own_or_admin(self, interaction: discord.Interaction, movie_name: str):
        all_movies = await self.bot.db.get_movies_data()
        # only unwatched movies
        movies = [movie for movie in all_movies if not movie.watched]
        if not (
            interaction.user.guild_permissions.administrator or interaction.user.get_role(NERDIOWO_MANAGE_SERVER_ID)
        ):
            movies = [movie for movie in movies if movie.suggestor == interaction.user.id]
        return [
            discord.app_commands.Choice(name=movie.title, value=movie.title)
            for movie in movies
            if movie_name.lower() in movie.title.lower()
        ]

    @remove_movie.autocomplete('movie_name')
    async def remove_movie_autocomplete(self, interaction: discord.Interaction, movie_name: str):
        return await self.autocomplete_unwatched_own_or_admin(interaction, movie_name)

    @nerdiowo_movies.command(name="start-vote", description="[admin only] Start the vote for the next movie")
    async def start_vote(self, interaction: discord.Interaction):
        if not (
            interaction.user.guild_permissions.administrator or interaction.user.get_role(NERDIOWO_MANAGE_SERVER_ID)
        ):
            await interaction.response.send_message("You are not an admin.", ephemeral=True)
            return
        all_movies = await self.bot.db.get_movies_data()
        # only unwatched movies
        movies = [movie for movie in all_movies if not movie.watched]
        if not movies:
            await interaction.response.send_message("There are no movies to vote on.", ephemeral=True)
            return
        # get 3 random movies
        if len(movies) < 3:
            random_movies = movies
        else:
            random_movies = random.sample(movies, 3)
        msg = "Vote for the next movie! React with the number of the movie you want to watch.\n"
        for i, movie in enumerate(random_movies):
            msg += f"{NUMBER_EMOJIS[i]} {movie.title} suggested by  <@{movie.suggestor}>\n"
        msg = await self.bot.get_channel(NERDIOWO_EVERYBODY_VOTES).send(
            msg, allowed_mentions=discord.AllowedMentions.none()
        )
        await interaction.response.send_message("Vote started.", ephemeral=True)
        thread = await msg.create_thread(name="Movie Night Vote")
        thread.send(
            f"{interaction.guild.get_role(NERDIOWO_EVERYBODY_VOTES).mention} Vote for the next movie!",
            allowed_mentions=discord.AllowedMentions.all(),
        )

    @nerdiowo_movies.command(name="create-event", description="[admin only] Create the movie night event")
    async def create_event(self, interaction: discord.Interaction, movie_name: str):
        if not (
            interaction.user.guild_permissions.administrator or interaction.user.get_role(NERDIOWO_MANAGE_SERVER_ID)
        ):
            log.debug(f"{interaction.user} is not an admin")
            await interaction.response.send_message("You are not an admin.", ephemeral=True)
            return
        all_movies = await self.bot.db.get_movies_data()
        # only unwatched movies
        movies = [movie for movie in all_movies if not movie.watched]
        log.debug(f"Found {len(movies)} unwatched movies")
        if not movies:
            await interaction.response.send_message("There are no movies to vote on.", ephemeral=True)
            return
        try:
            movie = [movie for movie in movies if movie.title == movie_name][0]
        except IndexError:
            await interaction.response.send_message("That movie has not been suggested", ephemeral=True)
            return
        await interaction.response.defer(thinking=True)
        log.debug(f"Creating event for movie {movie.title}")
        # the next time we watch a movie will  be the next time Saturday at 3:30PM Alaska time happens.
        now = datetime.datetime.now(tz=pytz.timezone("America/Anchorage"))
        start_time = now.replace(hour=15, minute=25, second=0, microsecond=0)
        # set the day to saturday
        start_time += datetime.timedelta(days=(5 - start_time.weekday()) % 7)
        log.debug(f"inintial Next movie night will be at {start_time}")

        #  if the time has already passed, set it for next week
        if start_time < now:
            log.debug(f"Next movie night is in the past, setting it for next week")
            start_time += datetime.timedelta(days=7)
        log.debug(f"Creating event for {start_time} for movie {movie.title}")
        event = await interaction.guild.create_scheduled_event(
            name=f"Movie Night: {movie.title}",
            channel=interaction.guild.get_channel(NERDIOWO_VOICE_CHANNEL),
            start_time=start_time,
        )
        log.debug(f"Created event {event.url}")
        await interaction.followup.send("Event created.")
        await self.bot.get_channel(NERDIOWO_ANNOUNCENENTS).send(
            f"{event.url} <@&{NERDIOWO_MOVIE_NIGHT_ROLE}>",
            allowed_mentions=discord.AllowedMentions.all(),
        )

    @create_event.autocomplete('movie_name')
    async def create_event_autocomplete(self, interaction: discord.Interaction, movie_name: str):
        return await self.autocomplete_unwatched_movie(interaction, movie_name)

    @nerdiowo_movies.command(name="watched", description="[admin only] Mark a movie as watched")
    async def watched(self, interaction: discord.Interaction, *, movie_name: str):
        if not interaction.user.guild_permissions.administrator or interaction.user.get_role(NERDIOWO_MANAGE_SERVER_ID):
            await interaction.response.send_message("You are not an admin.", ephemeral=True)
            return
        all_movies = await self.bot.db.get_movies_data()
        # only unwatched movies
        try:
            movie = [movie for movie in all_movies if not movie.watched and movie.title == movie_name][0]
        except IndexError:
            await interaction.response.send_message("That movie has not been suggested", ephemeral=True)
            return
        movie.watched = True
        movie.watchdate = datetime.datetime.now().strftime("%Y-%m-%d")
        await self.bot.db.save_movies_data(all_movies)
        await interaction.response.send_message(f"{movie.title} has been marked as watched.")

    @watched.autocomplete('movie_name')
    async def watched_ac_movie_name(self, interaction: discord.Interaction, movie_name: str):
        return await self.autocomplete_unwatched_movie(interaction, movie_name)

    @nerdiowo_movies.command(name="rename", description="Remove a movie from the list")
    async def rename(self, interaction: discord.Interaction, old_name: str, new_name: str):
        all_movies = await self.bot.db.get_movies_data()
        try:
            movie = [movie for movie in all_movies if movie.title == old_name][0]
        except IndexError:
            await interaction.response.send_message("That movie has not been suggested", ephemeral=True)
            return
        if not (
            movie.suggestor == interaction.user.id
            or interaction.user.guild_permissions.administrator
            or interaction.user.get_role(NERDIOWO_MANAGE_SERVER_ID)
        ):
            await interaction.response.send_message("You did not suggest that movie", ephemeral=True)
            return
        movie.title = new_name
        await self.bot.db.save_movies_data(all_movies)
        await interaction.response.send_message(f"`{old_name}` has been renamed to `{new_name}`.")

    @rename.autocomplete('old_name')
    async def rename_ac_old_name(self, interaction: discord.Interaction, old_name: str):
        return await self.autocomplete_unwatched_own_or_admin(interaction, old_name)


async def setup(bot):
    await bot.add_cog(NerdiowoMovies(bot))
