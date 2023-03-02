# copied from https://github.com/regulad/PepperCord/tree/main/src/utils/fixes.py

import shlex
import subprocess
from io import BytesIO

import discord
from discord.opus import Encoder


class FFmpegPCMAudioBytes(discord.AudioSource):
    """A hacky workaround to playing PCM audio with bytes."""

    def __init__(
        self, source: bytes, *, executable="ffmpeg", pipe=False, stderr=None, before_options=None, options=None
    ):
        stdin = None if not pipe else source
        args = [executable]
        if isinstance(before_options, str):
            args.extend(shlex.split(before_options))
        args.append("-i")
        args.append("-" if pipe else source)
        args.extend(("-f", "s16le", "-ar", "48000", "-ac", "2", "-loglevel", "warning"))
        if isinstance(options, str):
            args.extend(shlex.split(options))
        args.append("pipe:1")
        self._process = None
        try:
            self._process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr)
            self._stdout = BytesIO(self._process.communicate(input=stdin)[0])
        except FileNotFoundError:
            raise discord.ClientException(executable + " was not found.") from None
        except subprocess.SubprocessError as exc:
            raise discord.ClientException("Popen failed: {0.__class__.__name__}: {0}".format(exc)) from exc

    def read(self):
        ret = self._stdout.read(Encoder.FRAME_SIZE)
        if len(ret) != Encoder.FRAME_SIZE:
            return b""
        return ret

    def cleanup(self):
        proc = self._process
        if proc is None:
            return
        proc.kill()
        if proc.poll() is None:
            proc.communicate()

        self._process = None


__all__: list[str] = ["FFmpegPCMAudioBytes"]
