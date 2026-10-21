"""Local text-to-speech models besides Piper, all on this computer:

    kokoro    Kokoro-82M through kokoro-onnx: 54 natural voices in nine languages, offline.
              `halcyon assistant setup --kokoro` installs it (~340 MB). Voices: af_heart, bf_emma, am_adam, ...
    command   any program of your own (Coqui TTS, a Kokoro or F5 script, sherpa-onnx, ...): it gets the text on
              stdin, and either plays it itself or writes a WAV to stdout, which is played at your volume. The
              setting is the command line, split like a shell would but never run through one.

A local server that speaks OpenAI's /audio/speech (Kokoro-FastAPI, LocalAI, openedai-speech) is the AI voice with
its endpoint set to it, and needs no key: see tts_ai.py.
"""

from __future__ import annotations

import importlib.util
import shlex
import subprocess
import tempfile
import urllib.request
from pathlib import Path

from . import config

KOKORO_BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
KOKORO_FILES = ("kokoro-v1.0.onnx", "voices-v1.0.bin")
KOKORO_VOICE = "af_heart"
KOKORO_RATE = 24000
# A Kokoro voice's first letter is its language.
KOKORO_LANG = {"a": "en-us", "b": "en-gb", "e": "es", "f": "fr-fr", "h": "hi", "i": "it", "j": "ja", "p": "pt-br",
               "z": "cmn"}


class LocalVoiceError(Exception):
    pass


# --- Kokoro ------------------------------------------------------------------------------------------------------

def kokoro_dir() -> Path:
    return config.MODELS / "kokoro"


def kokoro_installed() -> bool:
    """The package (in the assistant's Python) and both model files."""
    return (importlib.util.find_spec("kokoro_onnx") is not None
            and all((kokoro_dir() / name).is_file() for name in KOKORO_FILES))


_kokoro = None


def _model():
    global _kokoro
    if _kokoro is None:
        from kokoro_onnx import Kokoro   # loaded once: the model takes a second or two
        _kokoro = Kokoro(str(kokoro_dir() / KOKORO_FILES[0]), str(kokoro_dir() / KOKORO_FILES[1]))
    return _kokoro


def kokoro_voices() -> list[str]:
    return sorted(_model().get_voices()) if kokoro_installed() else []


def kokoro_lang(voice: str) -> str:
    return KOKORO_LANG.get((voice or "a")[0], "en-us")


def kokoro_pcm(text: str, settings) -> tuple[bytes, int]:
    if not kokoro_installed():
        raise LocalVoiceError("Kokoro is not set up: halcyon assistant setup --kokoro")
    voice = settings.get("kokoroVoice") or KOKORO_VOICE
    try:
        samples, rate = _model().create(text, voice=voice, lang=kokoro_lang(voice))
    except Exception as error:     # an unknown voice, a phonemizer problem: say which
        raise LocalVoiceError(f"Kokoro: {error}") from None
    import numpy
    pcm = (numpy.clip(samples, -1.0, 1.0) * 32767).astype("<i2").tobytes()
    return pcm, int(rate)


def kokoro_download(progress=print) -> None:
    folder = kokoro_dir()
    folder.mkdir(parents=True, exist_ok=True)
    for name in KOKORO_FILES:
        target = folder / name
        if target.is_file():
            continue
        progress(f"downloading {name}…")
        part = target.with_name(name + ".part")
        with urllib.request.urlopen(KOKORO_BASE + name, timeout=60) as response, open(part, "wb") as out:
            while chunk := response.read(1 << 20):
                out.write(chunk)
        part.replace(target)


# --- a command of your own -------------------------------------------------------------------------------------

def command_configured(settings) -> bool:
    return bool((settings.get("ttsCommand") or "").strip())


def run_command(text: str, settings, timeout: int = 120) -> tuple[bytes | None, str | None]:
    """Run the command with the text on stdin. Returns (WAV bytes or None when it played itself, problem or None)."""
    try:
        argv = shlex.split(settings.get("ttsCommand") or "")
    except ValueError as error:
        return None, f"the voice command can't be read: {error}"
    if not argv:
        return None, "no voice command is set"
    try:
        done = subprocess.run(argv, input=text.encode(), capture_output=True, timeout=timeout, check=False)
    except FileNotFoundError:
        return None, f"{argv[0]} is not installed"
    except (OSError, subprocess.TimeoutExpired) as error:
        return None, f"{argv[0]}: {error}"
    if done.returncode != 0:
        return None, f"{argv[0]} exited {done.returncode}: {done.stderr.decode(errors='replace').strip()[-300:] or 'no message'}"
    if done.stdout[:4] == b"RIFF":
        return done.stdout, None
    return None, None


def wav_file(data: bytes) -> Path:
    handle = tempfile.NamedTemporaryFile(prefix="halcyon-voice-", suffix=".wav", delete=False)
    with handle:
        handle.write(data)
    return Path(handle.name)
