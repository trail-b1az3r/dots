"""Speech to text.

whisper.cpp is the target: one static binary, a GGML model file, no
Python dependencies, and it runs usefully on a CPU. faster-whisper is
used when it happens to be installed. Everything is invoked as a
subprocess with an argv list.
"""

from __future__ import annotations

import glob
import json
import os
import re
import shutil
import subprocess
from typing import Any

from .. import paths

#: Where distributions and whisper.cpp itself put model files.
MODEL_DIRS = [
    str(paths.DATA_DIR / "models" / "whisper"),
    os.path.expanduser("~/.local/share/whisper"),
    os.path.expanduser("~/.cache/whisper"),
    "/usr/share/whisper.cpp",
    "/usr/share/whisper",
    "/var/lib/whisper",
]

_BINARIES = ("whisper-cli", "whisper-cpp", "whisper", "main")


def binary() -> str | None:
    for name in _BINARIES:
        found = shutil.which(name)
        if found:
            return found
    return None


def find_model(preferred: str = "") -> str | None:
    """Locate a GGML model, preferring the configured one."""
    if preferred:
        expanded = os.path.expanduser(preferred)
        if os.path.isfile(expanded):
            return expanded

    candidates: list[str] = []
    for directory in MODEL_DIRS:
        candidates.extend(sorted(glob.glob(os.path.join(directory, "ggml-*.bin"))))
    if not candidates:
        return None

    # Prefer the smallest useful model so first use is not a five-minute
    # wait on a laptop CPU.
    for preference in ("base.en", "base", "small.en", "small", "tiny.en", "tiny"):
        for candidate in candidates:
            if preference in os.path.basename(candidate):
                return candidate
    return candidates[0]


def available(settings: dict[str, Any]) -> bool:
    local = settings.get("assistant", {}).get("local", {})
    backend = str(local.get("sttBackend", "whisper-cpp"))
    if backend == "faster-whisper":
        return shutil.which("faster-whisper") is not None
    return binary() is not None and find_model(str(local.get("sttModel", ""))) is not None


def describe(settings: dict[str, Any]) -> str:
    local = settings.get("assistant", {}).get("local", {})
    exe = binary()
    if exe is None:
        return "not installed"
    model = find_model(str(local.get("sttModel", "")))
    if model is None:
        return f"{os.path.basename(exe)} (no model found)"
    return f"{os.path.basename(exe)} · {os.path.basename(model)}"


_TIMESTAMP = re.compile(r"^\s*\[[\d:.\s\->]+\]\s*")


def transcribe(wav_path: str, settings: dict[str, Any]) -> tuple[bool, str]:
    """Return `(ok, text)`. `ok` is False with a reason when it cannot run."""
    if not os.path.isfile(wav_path):
        return False, "the recording disappeared"

    local = settings.get("assistant", {}).get("local", {})
    language = "auto"

    if str(local.get("sttBackend", "whisper-cpp")) == "faster-whisper":
        exe = shutil.which("faster-whisper")
        if exe is None:
            return False, "faster-whisper is not installed"
        argv = [exe, "--model", str(local.get("sttModel") or "base"), "--output_format", "txt", wav_path]
        try:
            done = subprocess.run(argv, capture_output=True, text=True, timeout=180, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return False, str(exc)
        return (done.returncode == 0, done.stdout.strip())

    exe = binary()
    if exe is None:
        return False, "no speech-to-text engine is installed (whisper.cpp)"
    model = find_model(str(local.get("sttModel", "")))
    if model is None:
        return False, (
            "no whisper model was found — put a ggml-*.bin file in "
            f"{MODEL_DIRS[0]}"
        )

    argv = [
        exe,
        "-m", model,
        "-f", wav_path,
        "-nt",              # no timestamps
        "-np",              # no progress prints
        "-l", language,
        "-t", str(max(1, min(8, (os.cpu_count() or 4) // 2))),
    ]
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=240, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)

    if done.returncode != 0:
        detail = done.stderr.strip().splitlines()
        return False, detail[-1] if detail else "the transcriber failed"

    lines = [
        _TIMESTAMP.sub("", line).strip()
        for line in done.stdout.splitlines()
        if line.strip()
    ]
    text = " ".join(line for line in lines if line)
    # whisper emits bracketed markers for non-speech; they are not words.
    text = re.sub(r"[\[(](?:BLANK_AUDIO|inaudible|music|silence)[\])]", "", text, flags=re.I)
    return True, text.strip()
