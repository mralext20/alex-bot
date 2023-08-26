import asyncio
import ctypes
import dataclasses
import io
import logging
import os
import uuid
from typing import Dict, List, Optional, Tuple

import discord
from asyncgTTS import AsyncGTTSSession, ServiceAccount, SynthesisInput, TextSynthesizeRequestBody, VoiceSelectionParams
from discord import app_commands

from alexBot.classes import googleVoices as voices
from alexBot.database import UserConfig, async_session, select
from alexBot.tools import Cog

log = logging.getLogger(__name__)


wavenetChoices = [discord.app_commands.Choice(name=f"WaveNet {v[0][-1]} ({v[1]})", value=v[0]) for v in voices]


# TODO:
# - line limit?
# queue?
# link parsing
# emoji parsing
# any mentions parsing
# spoiler hiding
# multi-user per vc / guild at same time
# better voice model selection , name of the config, from db, uh that other thing
@dataclasses.dataclass
class TTSUserInstance:
    vsParams: VoiceSelectionParams
    channel: discord.TextChannel


@dataclasses.dataclass
class TTSInstance:
    voiceClient: discord.VoiceClient
    users: Dict[int, TTSUserInstance] = dataclasses.field(default_factory=dict)
    queue: List[discord.AudioSource] = dataclasses.field(default_factory=list)


class VoiceTTS(Cog):
    def __init__(self, bot):
        super().__init__(bot)
        self.runningTTS: Dict[int, TTSInstance] = {}
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
        self.bot.voiceCommandsGroup.remove_command("tts")
        for vc in self.runningTTS.values():
            await vc.voiceClient.disconnect()
        await self.gtts.__aexit__(None, None, None)

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if (
            message.guild
            and message.guild.id in self.runningTTS
            and message.author.id in self.runningTTS[message.guild.id].users
            and self.runningTTS[message.guild.id].users[message.author.id].channel.id == message.channel.id
        ):
            await self.sendTTS(
                message.content,
                self.runningTTS[message.guild.id],
                self.runningTTS[message.guild.id].users[message.author.id],
            )

    @Cog.listener()
    async def on_voice_state_update(
        self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ):
        if after.channel is not None:
            return
        # someone left a voice channel. do we care?
        if member.guild and member.guild.id in self.runningTTS and member.id in self.runningTTS[member.guild.id].users:
            del self.runningTTS[member.guild.id].users[member.id]

        if self.bot.user.id == member.id and after.channel is None and member.guild.id in self.runningTTS:
            del self.runningTTS[member.guild.id]

    async def sendTTS(self, text: str, ttsInstance: TTSInstance, ttsUser: TTSUserInstance):
        vc = ttsInstance.voiceClient
        if not vc.is_connected():
            self.runningTTS
            return
        log.debug(f"Sending TTS: {text=}")
        try:
            synth_bytes = await self.gtts.synthesize(
                TextSynthesizeRequestBody(SynthesisInput(text), voice_input=ttsUser.vsParams)
            )
        except Exception as e:
            log.exception(e)
            return
        buff_sound = io.BytesIO(synth_bytes)

        sound = discord.FFmpegOpusAudio(buff_sound, pipe=True)
        ttsInstance.queue.append(sound)
        if not vc.is_playing():
            await self.queue_handler(ttsInstance)

    async def queue_handler(self, instance: TTSInstance):
        if instance.voiceClient.is_playing():
            return
        while len(instance.queue) > 0:
            if instance.voiceClient.is_playing():
                await asyncio.sleep(0.25)
                continue
            next = instance.queue.pop(0)
            instance.voiceClient.play(next, after=self.after)
            await asyncio.sleep(0.25)

    async def model_autocomplete(
        self, interaction: discord.Interaction, guess: str
    ) -> List[discord.app_commands.Choice]:
        chc = []
        if interaction.guild_id and interaction.guild_id in self.runningTTS:
            instance = self.runningTTS[interaction.guild_id]
            existing = [z.vsParams.name for z in instance.users.values()]
            for choice in wavenetChoices:
                if choice.name not in existing:
                    chc.append(discord.app_commands.Choice(name=choice.name, value=choice.value))
        else:
            chc = [z for z in wavenetChoices]
        async with async_session() as db_session:
            userData = await db_session.scalar(select(UserConfig).where(UserConfig.userId == interaction.user.id))
            if userData and userData.voiceModel:
                chc.append(discord.app_commands.Choice(name=f"SAVED ({userData.voiceModel})", value="SAVED"))
        return chc

    @app_commands.autocomplete(model=model_autocomplete)
    async def vc_tts(self, interaction: discord.Interaction, model: str):
        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in a guild", ephemeral=True)
            return

        if interaction.user.voice is None:
            await interaction.response.send_message("You are not in a voice channel", ephemeral=True)
            return

        if model == "SAVED":
            # we pull from database, and use that
            async with async_session() as session:
                userData = await session.scalar(select(UserConfig).where(UserConfig.userId == interaction.user.id))
                if not userData:
                    userData = UserConfig(interaction.user.id)
                    session.add(userData)
                    await session.commit()
                    await interaction.response.send_message(
                        "You have not set a voice preference. use `/config user set` to set one", ephemeral=True
                    )
                    return
                if not userData.voiceModel:
                    await interaction.response.send_message(
                        "You have not set a voice preference. use `/config user set` to set one", ephemeral=True
                    )
                    return
                model = userData.voiceModel

        if interaction.guild.id not in self.runningTTS:
            vc = await interaction.user.voice.channel.connect()
            self.runningTTS[interaction.guild.id] = TTSInstance(vc)

        self.runningTTS[interaction.guild.id].users[interaction.user.id] = TTSUserInstance(
            VoiceSelectionParams(language_code="en-US", name=model),
            interaction.channel,
        )

        await interaction.response.send_message(
            "TTS is now enabled for you. leaving the voice channel will end your tts.", ephemeral=False
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
