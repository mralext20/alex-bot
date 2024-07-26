import functools
import io
import logging

import discord
from discord import app_commands
import pydub
import speech_recognition

from alexBot import database as db

from ..tools import Cog

log = logging.getLogger(__name__)


class VoiceMessageTranscriber(Cog):
    def __init__(self, bot):
        super().__init__(bot)

        self.voiceMessageTranscriberMenu = app_commands.ContextMenu(
            name='Transcribe Voice Message',
            callback=self.transcribe_command_on_demand,
            allowed_contexts=app_commands.AppCommandContext(guild=True, dm_channel=True, private_channel=True),
            allowed_installs=app_commands.AppInstallationType(guild=True, user=True),
        )

    async def cog_load(self) -> None:
        commands = [
            self.voiceMessageTranscriberMenu,
        ]
        for command in commands:
            self.bot.tree.add_command(command)

    async def cog_unload(self) -> None:
        commands = [
            self.voiceMessageTranscriberMenu,
        ]
        for command in commands:
            self.bot.tree.remove_command(command.name, type=command.type)

    async def transcribe_command_on_demand(self, interaction: discord.Interaction, message: discord.Message):

        be_ephemeral = interaction.is_user_integration()  # True if user context, False if guild context
        """transcribe this specifc message"""
        if not message.flags.voice:
            return await interaction.response.send_message("Message is not a voice message!", ephemeral=True)
        if message.attachments[0].content_type != "audio/ogg":
            log.debug(f"Transcription failed! Attachment not a Voice Message. message.id={message.id}")
            return await interaction.response.send_message(
                "Transcription failed! (Attachment not a Voice Message)", ephemeral=True
            )

        await interaction.response.defer(ephemeral=be_ephemeral)

        # Read voice file and converts it into something pydub can work with
        log.debug(f"Reading voice file. message.id={message.id}")
        voice_file = await message.attachments[0].read()
        voice_file = io.BytesIO(voice_file)

        result = await self.transcribe(voice_file)
        await interaction.followup.send(
            content=f"**Audio Message Transcription:\n** ```{result}```", ephemeral=be_ephemeral
        )

    async def transcribe(self, audio: io.BytesIO) -> str:
        x = await self.bot.loop.run_in_executor(None, pydub.AudioSegment.from_file, audio)
        new = io.BytesIO()
        await self.bot.loop.run_in_executor(None, functools.partial(x.export, new, format='wav'))

        # Convert .wav file into speech_recognition's AudioFile format or whatever idrk
        log.debug("Converting file to AudioFile format.")
        recognizer = speech_recognition.Recognizer()
        with speech_recognition.AudioFile(new) as source:
            audio = await self.bot.loop.run_in_executor(None, recognizer.record, source)

        # Runs the file through OpenAI Whisper
        log.debug("Running file through OpenAI Whisper.")
        result = await self.bot.loop.run_in_executor(None, recognizer.recognize_whisper, audio)
        return result if result != "" else "*Nothing*"

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        # message in a guild
        if not message.guild:
            return
        if not message.flags.voice:
            return
        log.debug(f"Getting guild data for {message.guild}")
        gc = None
        async with db.async_session() as session:
            gc = await session.get(db.GuildConfig, message.guild.id)
            if not gc:
                gc = db.GuildConfig(guildId=message.guild.id)
                session.add(gc)
                await session.commit()

        if gc.transcribeVoiceMessages:
            if message.attachments[0].content_type != "audio/ogg":
                log.debug(f"Transcription failed! Attachment not a Voice Message. message.id={message.id}")
                await message.reply("Transcription failed! (Attachment not a Voice Message)", mention_author=False)
                return

            msg = await message.reply("✨ Transcribing...", mention_author=False)

            # Read voice file and converts it into something pydub can work with
            log.debug(f"Reading voice file. message.id={message.id}")
            voice_file = await message.attachments[0].read()
            voice_file = io.BytesIO(voice_file)

            result = await self.transcribe(voice_file)
            await msg.edit(content=f"**Audio Message Transcription:\n** ```{result}```")


async def setup(bot):
    await bot.add_cog(VoiceMessageTranscriber(bot))
