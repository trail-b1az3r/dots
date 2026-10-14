"""Raw PCM in and out: the commands that record and play headerless 16-bit audio.

PipeWire changed what `-` means. Up to 1.0, `pw-record -` and `pw-play -` streamed raw samples. From 1.2, `-` is
a sound *file* on stdin or stdout (Sun AU, big-endian, with a header), and raw needs `--raw`. Arch ships 1.4, so
the old commands recorded noise (the AU header and byte-swapped samples, read as raw) and played nothing. That
broke the wake word, the transcription, the chimes and the voice. These commands ask `pw-cat` which it is.
"""

from __future__ import annotations

import functools
import shutil
import subprocess


@functools.lru_cache(maxsize=1)
def pipewire_has_raw() -> bool:
    """Whether this pw-cat takes --raw (PipeWire 1.2 and later)."""
    tool = shutil.which("pw-cat") or shutil.which("pw-play") or shutil.which("pw-record")
    if not tool:
        return False
    try:
        out = subprocess.run([tool, "--help"], capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.SubprocessError):
        return False
    return "--raw" in (out.stdout + out.stderr)


def _pipewire(tool: str, rate: int, channels: int) -> list[str]:
    command = [tool]
    if pipewire_has_raw():
        command.append("--raw")
    return command + ["--rate", str(rate), "--channels", str(channels), "--format", "s16", "-"]


def player(rate: int, channels: int = 1) -> list[str] | None:
    """A command that plays raw s16 PCM from stdin, or None when there is no player."""
    if shutil.which("pw-play"):
        return _pipewire("pw-play", rate, channels)
    if shutil.which("paplay"):
        return ["paplay", "--raw", f"--rate={rate}", f"--channels={channels}", "--format=s16le"]
    if shutil.which("aplay"):
        return ["aplay", "-q", "-r", str(rate), "-f", "S16_LE", "-c", str(channels), "-t", "raw"]
    return None


def recorder(rate: int, channels: int = 1) -> list[str] | None:
    """A command that writes raw s16 PCM from the default microphone to stdout, or None."""
    if shutil.which("pw-record"):
        return _pipewire("pw-record", rate, channels)
    if shutil.which("parec"):
        return ["parec", f"--rate={rate}", f"--channels={channels}", "--format=s16le"]
    if shutil.which("arecord"):
        return ["arecord", "-q", "-f", "S16_LE", "-r", str(rate), "-c", str(channels), "-t", "raw"]
    return None
