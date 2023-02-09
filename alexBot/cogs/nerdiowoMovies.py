# -*- coding: utf-8 -*-

import datetime
import random

import discord
from discord.ext.commands import Paginator
from jishaku.paginators import PaginatorInterface

from alexBot.classes import MovieSuggestion

from ..tools import Cog

NERDIOWO_EVERYBODY_VOTES = 847555306166943755
NERDIOWO_MANAGE_SERVER_ID = 1046177820285603881


class NerdiowoMovies(Cog):
    def __init__(self, bot):
        super().__init__(bot)

    nerdiowo_movies = discord.app_commands.Group(
        name="movies",
        description="nerdiowo movies menu",
        guild_ids=[791528974442299412],
    )

    @nerdiowo_movies.command(name="list", description="list all movies")
    async def list_movies(self, interaction: discord.Interaction):
        all_movies = await self.bot.db.get_movies_data()

        jishaku = self.bot.get_cog("Jishaku")
        if not jishaku:
            await interaction.response.send_message("Jishaku is not loaded.", ephemeral=True)
            return
        paginator = Paginator(prefix="```", suffix="```", max_size=500)
        for movie in all_movies:
            paginator.add_line(
                f"{movie.title} - {movie.suggestor}{f' - watched on {movie.watchdate}' if movie.watched else ''}"
            )
        pi = PaginatorInterface(self.bot, paginator, owner=None)
        await pi.send_to(interaction.channel)
        await interaction.response.send_message("sent", ephemeral=True)

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
        suggestion = MovieSuggestion(title=movie_name, watched=False, suggestor=interaction.user.id, watchdate="")
        all_movies.append(suggestion)
        await self.bot.db.save_movies_data(all_movies)
        await interaction.response.send_message(f"Your movie suggestion, {suggestion.title} has been submitted.")

    @nerdiowo_movies.command(name="start-vote", description="[admin only] Start the vote for the next movie")
    async def start_vote(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator or interaction.user.get_role(NERDIOWO_MANAGE_SERVER_ID):
            await interaction.response.send_message("You are not an admin.", ephemeral=True)
            return
        all_movies = await self.bot.db.get_movies_data()
        # only unwatched movies
        movies = [movie for movie in all_movies if not movie.watched]
        if not movies:
            await interaction.response.send_message("There are no movies to vote on.", ephemeral=True)
            return
        # get 3 random movies
        random_movies = random.sample(movies, 3)
        await self.bot.get_channel(NERDIOWO_EVERYBODY_VOTES).send(
            f"next movie for movie night:\n1️⃣: {random_movies[0].title} submitted by <@{random_movies[0].suggestor}>\n2️⃣: {random_movies[1].title} submitted by <@{random_movies[1].suggestor}>\n3️⃣: {random_movies[2].title} submitted by <@{random_movies[2].suggestor}>"
        )
        await interaction.response.send_message("Vote started.")

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
        all_movies = await self.bot.db.get_movies_data()
        # only unwatched movies
        movies = [movie for movie in all_movies if not movie.watched]
        return [
            discord.app_commands.Choice(name=movie.title, value=movie.title)
            for movie in movies
            if movie_name.lower() in movie.title.lower()
        ]


async def setup(bot):
    await bot.add_cog(NerdiowoMovies(bot))
