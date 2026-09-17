"""Text to speech.

Piper is the target: a small ONNX voice, good quality, no network, and a
plain stdin/stdout interface. espeak-ng is the fallback — it sounds like
1998, but a robotic answer beats silence when someone has asked a
question with their hands full.
"""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
import tempfile
from typing import Any

from .. import paths

VOICE_DIRS = [
    str(paths.DATA_DIR / "models" / "piper"),
    os.path.expanduser("~/.local/share/piper-voices"),
    os.path.expanduser("~/.local/share/piper"),
    "/usr/share/piper-voices",
    "/usr/share/piper",
]


def binary() -> str | None:
    for name in ("piper", "piper-tts"):
        found = shutil.which(name)
        if found:
            return found
    return None


def find_voice(preferred: str = "") -> str | None:
    if preferred:
        expanded = os.path.expanduser(preferred)
        if os.path.isfile(expanded):
            return expanded

    candidates: list[str] = []
    for directory in VOICE_DIRS:
        candidates.extend(sorted(glob.glob(os.path.join(directory, "**", "*.onnx"), recursive=True)))
    if not candidates:
        return None
    if preferred:
        for candidate in candidates:
            if preferred in os.path.basename(candidate):
                return candidate
    return candidates[0]


def available(settings: dict[str, Any]) -> bool:
    voice = settings.get("assistant", {}).get("voice", {})
    if binary() is not None and find_voice(str(voice.get("name", ""))) is not None:
        return True
    return shutil.which("espeak-ng") is not None


def describe(settings: dict[str, Any]) -> str:
    voice = settings.get("assistant", {}).get("voice", {})
    exe = binary()
    if exe is not None:
        model = find_voice(str(voice.get("name", "")))
        if model is not None:
            return f"piper · {os.path.basename(model)}"
        return "piper (no voice model found)"
    if shutil.which("espeak-ng"):
        return "espeak-ng (fallback)"
    return "not installed"


def synthesise(text: str, settings: dict[str, Any]) -> str | None:
    """Render speech to a WAV file, returning its path."""
    text = text.strip()
    if not text:
        return None
    # A paragraph of synthesis is slow and nobody listens to all of it.
    if len(text) > 1200:
        text = text[:1200].rsplit(".", 1)[0] + "."

    voice_settings = settings.get("assistant", {}).get("voice", {})
    speed = float(voice_settings.get("speed", 1.0) or 1.0)

    handle, target = tempfile.mkstemp(prefix="halcyon-tts-", suffix=".wav")
    os.close(handle)

    exe = binary()
    model = find_voice(str(voice_settings.get("name", ""))) if exe else None

    if exe and model:
        argv = [exe, "--model", model, "--output_file", target]
        if speed and abs(speed - 1.0) > 0.01:
            # Piper expresses speed as a length scale: higher is slower.
            argv += ["--length_scale", f"{1.0 / max(0.4, min(2.5, speed)):.3f}"]
        try:
            done = subprocess.run(
                argv, input=text, text=True, capture_output=True, timeout=120, check=False
            )
        except (OSError, subprocess.TimeoutExpired):
            done = None
        if done is not None and done.returncode == 0 and os.path.getsize(target) > 128:
            return target

    if shutil.which("espeak-ng"):
        words_per_minute = int(max(80, min(320, 165 * speed)))
        try:
            done = subprocess.run(
                ["espeak-ng", "-s", str(words_per_minute), "-w", target, text],
                capture_output=True, timeout=60, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            done = None
        if done is not None and done.returncode == 0 and os.path.getsize(target) > 128:
            return target

    try:
        os.unlink(target)
    except OSError:
        pass
    return None
