import functools
import io
import logging

import discord
import pydub
import speech_recognition

from alexBot import database as db

from ..tools import Cog

log = logging.getLogger(__name__)


class VoiceMessageTranscriber(Cog):
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

            # Convert original .ogg file into a .wav file
            log.debug(f"Converting file format to .wav. message.id={message.id}")
            x = await self.bot.loop.run_in_executor(None, pydub.AudioSegment.from_file, voice_file)
            new = io.BytesIO()
            await self.bot.loop.run_in_executor(None, functools.partial(x.export, new, format='wav'))

            # Convert .wav file into speech_recognition's AudioFile format or whatever idrk
            log.debug(f"Converting file to AudioFile format. message.id={message.id}")
            recognizer = speech_recognition.Recognizer()
            with speech_recognition.AudioFile(new) as source:
                audio = await self.bot.loop.run_in_executor(None, recognizer.record, source)

            # Runs the file through OpenAI Whisper
            log.debug(f"Running file through OpenAI Whisper. message.id={message.id}")
            result = await self.bot.loop.run_in_executor(None, recognizer.recognize_whisper, audio)
            if result == "":
                result = "*nothing*"

            # Edit the original message with the transcription result
            log.debug(f"Editing message with transcription result. message.id={message.id}")
            await msg.edit(content=f"**Audio Message Transcription:\n** ```{result}```")


async def setup(bot):
    await bot.add_cog(VoiceMessageTranscriber(bot))
