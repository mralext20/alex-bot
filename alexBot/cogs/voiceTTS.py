import asyncio
import ctypes
import logging
import os
import uuid
from typing import Dict, List, Optional, Tuple

import discord
from asyncgTTS import AsyncGTTSSession, ServiceAccount, SynthesisInput, TextSynthesizeRequestBody, VoiceSelectionParams
from discord import app_commands

from alexBot.database import async_session, select, UserConfig
from alexBot.classes import googleVoices as voices

from alexBot.tools import Cog

log = logging.getLogger(__name__)


wavenetChoices = [discord.app_commands.Choice(name=f"WaveNet {v[0][-1]} ({v[1]})", value=v[0]) for v in voices]
wavenetChoices.append(discord.app_commands.Choice(name="Saved Preference (in /config user)", value="SAVED"))


class VoiceTTS(Cog):
    def __init__(self, bot: "Bot"):
        super().__init__(bot)
        self.runningTTS: Dict[int, Tuple[discord.TextChannel, discord.VoiceClient, VoiceSelectionParams]] = {}
        self.gtts: AsyncGTTSSession = None

    async def cog_load(self):
        self.gtts = AsyncGTTSSession.from_service_account(
            ServiceAccount.from_service_account_dict(self.bot.config.google_service_account),
        )

        self.bot.voiceCommandsGroup.add_command(
            app_commands.Command(name="tts", description="Send text to speech", callback=self.vc_tts)
        )

        await self.gtts.__aenter__()

    async def cog_unload(self) -> None:
        for vc in self.runningTTS.values():
            await vc[1].disconnect()
        await self.gtts.__aexit__(None, None, None)
        self.bot.voiceCommandsGroup.remove_command("tts")

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id in self.runningTTS and message.channel.id == self.runningTTS[message.author.id][0].id:
            await self.sendTTS(message.content, self.runningTTS[message.author.id])

    @Cog.listener()
    async def on_voice_state_update(
        self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ):
        if member.id in self.runningTTS and after.channel != self.runningTTS[member.id][1].channel:
            await self.runningTTS[member.id][1].disconnect()
            del self.runningTTS[member.id]

    async def sendTTS(self, text: str, extra: Tuple[discord.TextChannel, discord.VoiceClient, VoiceSelectionParams]):
        channel, vc, voiceType = extra
        mid = uuid.uuid4()
        if not vc.is_connected():
            del self.runningTTS[channel.guild.id]
            return
        log.debug(f"Sending TTS: {text=}")
        try:
            synth_bytes = await self.gtts.synthesize(
                TextSynthesizeRequestBody(SynthesisInput(text), voice_input=voiceType)
            )
        except Exception as e:
            log.exception(e)
            return
        f_name = f"tts_{mid}.ogg"
        f = open(f_name, "wb")
        f.write(synth_bytes)
        f.close()
        sound = await discord.FFmpegOpusAudio.from_probe(f_name)
        vc.play(sound, after=self.after)
        while vc.is_playing():
            await asyncio.sleep(0.5)
        os.remove(f_name)

    @app_commands.choices(model=wavenetChoices)
    async def vc_tts(self, interaction: discord.Interaction, model: str):
        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in a guild", ephemeral=True)
            return

        if interaction.user.voice is None:
            await interaction.response.send_message("You are not in a voice channel", ephemeral=True)
            return
        vc = await interaction.user.voice.channel.connect()

        if model == "SAVED":
            # we pull from database, and use that
            async with async_session() as session:
                userData = await session.scalar(select(UserConfig).where(UserConfig.userId == interaction.user.id))
                if not userData:
                    userData = UserConfig(interaction.user.id)
                    session.add(userData)
                    await session.commit()
                    await interaction.response.send_message(
                        "You have not set a voice preference. use `/config user` to set one", ephemeral=True
                    )
                    return
                if not userData.voiceModel:
                    await interaction.response.send_message(
                        "You have not set a voice preference. use `/config user set` to set one", ephemeral=True
                    )
                    return
                model = userData.voiceModel

        self.runningTTS[interaction.user.id] = (
            interaction.channel,
            vc,
            VoiceSelectionParams(language_code="en-US", name=model),
        )
        await interaction.response.send_message(
            "TTS is now for you in this channel. leaving the voice channel will end the tts.", ephemeral=False
        )

    def after(self, error: Optional[Exception]):
        log.debug(f"after: {error=}")
        if error:
            log.exception(error)


async def setup(bot):
    try:
        discord.opus.load_opus(ctypes.util.find_library("opus"))
    except Exception as e:
        log.exception(e)
        log.error("Could not load opus library")
        log.error('not loading voiceTTS module')
        return
    await bot.add_cog(VoiceTTS(bot))
