"""Recording and playback, using whatever the machine already has.

No Python audio bindings. `sounddevice` pulls in PortAudio and NumPy, and
the whole point of the local backend is that it works on a machine where
`pip install` is not an option. PipeWire's own `pw-record`/`pw-play` are
present wherever PipeWire is, with PulseAudio and ALSA as fallbacks.

Recording stops on silence rather than on a fixed timer, so push-to-talk
feels like talking rather than like operating a stopwatch.
"""

from __future__ import annotations

import array
import math
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass

SAMPLE_RATE = 16000  # what every speech model expects
CHANNELS = 1


@dataclass
class Recording:
    path: str
    seconds: float
    peak: float
    cancelled: bool = False


def _have(name: str) -> bool:
    return shutil.which(name) is not None


def recorder_available() -> bool:
    return any(_have(tool) for tool in ("pw-record", "parecord", "arecord"))


def player_available() -> bool:
    return any(_have(tool) for tool in ("pw-play", "paplay", "aplay"))


def _record_argv(target: str, device: str | None) -> list[str] | None:
    if _have("pw-record"):
        argv = ["pw-record", "--rate", str(SAMPLE_RATE), "--channels", str(CHANNELS)]
        if device and device != "default":
            argv += ["--target", device]
        return argv + [target]
    if _have("parecord"):
        argv = [
            "parecord", "--rate", str(SAMPLE_RATE), "--channels", str(CHANNELS),
            "--format", "s16le", "--file-format", "wav",
        ]
        if device and device != "default":
            argv += ["--device", device]
        return argv + [target]
    if _have("arecord"):
        return [
            "arecord", "-q", "-f", "S16_LE", "-r", str(SAMPLE_RATE),
            "-c", str(CHANNELS), "-t", "wav",
            *(["-D", device] if device and device != "default" else []),
            target,
        ]
    return None


def microphone_muted() -> bool:
    """True when the default source is muted.

    Recording a muted microphone produces a file of silence, the model
    transcribes nothing, and the user is told "I didn't catch that" — a
    confusing answer to a problem they can see on the bar. Better to say
    the microphone is muted.
    """
    from .. import desktop

    return bool(desktop.microphone_state().get("muted"))


def record(
    *,
    device: str | None = None,
    max_seconds: float = 20.0,
    silence_seconds: float = 1.2,
    silence_threshold: float = 0.012,
    should_stop=None,
) -> Recording | None:
    """Record until silence, a cancel signal, or the time limit.

    The level check reads the growing WAV file rather than piping audio
    through Python: the recorder writes, we sample the tail every 150 ms.
    That keeps CPU near zero while still ending the turn promptly.
    """
    handle, target = tempfile.mkstemp(prefix="halcyon-stt-", suffix=".wav")
    os.close(handle)

    argv = _record_argv(target, device)
    if argv is None:
        os.unlink(target)
        return None

    try:
        process = subprocess.Popen(
            argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except OSError:
        os.unlink(target)
        return None

    started = time.monotonic()
    last_voice = started
    peak = 0.0
    heard_anything = False
    cancelled = False

    try:
        while True:
            time.sleep(0.15)
            now = time.monotonic()

            if should_stop is not None and should_stop():
                cancelled = True
                break
            if now - started >= max_seconds:
                break

            level = _tail_level(target)
            peak = max(peak, level)
            if level >= silence_threshold:
                heard_anything = True
                last_voice = now
            elif heard_anything and (now - last_voice) >= silence_seconds:
                break
            elif not heard_anything and (now - started) >= 4.0:
                # Nothing at all after four seconds: the user probably
                # pressed the key by accident.
                break

            if process.poll() is not None:
                break
    finally:
        try:
            process.terminate()
            process.wait(timeout=2)
        except (OSError, subprocess.TimeoutExpired):
            try:
                process.kill()
            except OSError:
                pass

    seconds = time.monotonic() - started
    if cancelled or not heard_anything:
        try:
            os.unlink(target)
        except OSError:
            pass
        return Recording(path="", seconds=seconds, peak=peak, cancelled=cancelled)

    return Recording(path=target, seconds=seconds, peak=peak)


def _tail_level(path: str, window_bytes: int = 8192) -> float:
    """RMS of the most recent samples in a 16-bit mono WAV, as 0..1."""
    try:
        size = os.path.getsize(path)
        if size <= 64:
            return 0.0
        with open(path, "rb") as handle:
            start = max(44, size - window_bytes)
            handle.seek(start - (start % 2))
            raw = handle.read(window_bytes)
    except OSError:
        return 0.0

    if len(raw) < 2:
        return 0.0
    samples = array.array("h")
    samples.frombytes(raw[: len(raw) - (len(raw) % 2)])
    if not samples:
        return 0.0
    total = sum(float(sample) * sample for sample in samples)
    return math.sqrt(total / len(samples)) / 32768.0


def play(path: str, *, volume: float = 1.0) -> bool:
    """Play a WAV file. Blocks until it finishes."""
    if not os.path.isfile(path):
        return False
    volume = max(0.0, min(1.5, volume))

    if _have("pw-play"):
        argv = ["pw-play", "--volume", f"{volume:.2f}", path]
    elif _have("paplay"):
        argv = ["paplay", "--volume", str(int(volume * 65536)), path]
    elif _have("aplay"):
        argv = ["aplay", "-q", path]
    else:
        return False

    try:
        return subprocess.run(argv, timeout=180, check=False).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def play_async(path: str, *, volume: float = 1.0) -> subprocess.Popen | None:
    """Start playback without waiting, so a reply can be interrupted."""
    if not os.path.isfile(path):
        return None
    if _have("pw-play"):
        argv = ["pw-play", "--volume", f"{max(0.0, min(1.5, volume)):.2f}", path]
    elif _have("paplay"):
        argv = ["paplay", path]
    elif _have("aplay"):
        argv = ["aplay", "-q", path]
    else:
        return None
    try:
        return subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        return None
