"""Small pieces of runtime state shared between components.

Quickshell owns notification and assistant state; Waybar needs to display
a summary of it; the CLI sits between them. Rather than have Waybar poll,
the owner writes a tiny JSON file here and signals Waybar, which refreshes
the one module that changed. Two writes and one signal beats a timer that
fires whether or not anything happened.
"""

from __future__ import annotations

import json
import os
import signal
import tempfile
from typing import Any

from . import paths

#: Waybar real-time signal numbers, matching config/waybar/modules.jsonc.
WAYBAR_SIGNALS = {
    "notifications": 8,
    "assistant": 9,
    "power": 7,
}


def _path(name: str) -> str:
    return str(paths.STATE_DIR / f"{name}.json")


def read(name: str, default: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        with open(_path(name), "r", encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, ValueError):
        return dict(default or {})
    return value if isinstance(value, dict) else dict(default or {})


def write(name: str, payload: dict[str, Any], *, refresh: bool = True) -> None:
    paths.STATE_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(paths.STATE_DIR), prefix=f".{name}-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
        os.replace(tmp, _path(name))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    if refresh:
        refresh_waybar(name)


def refresh_waybar(name: str) -> bool:
    """Poke the Waybar module that displays `name`."""
    number = WAYBAR_SIGNALS.get(name)
    if number is None:
        return False
    return _signal_waybar(signal.SIGRTMIN + number)


def _signal_waybar(sig: int) -> bool:
    sent = False
    try:
        entries = os.listdir("/proc")
    except OSError:
        return False
    for entry in entries:
        if not entry.isdigit():
            continue
        try:
            with open(f"/proc/{entry}/comm", "r", encoding="utf-8") as handle:
                if handle.read().strip() != "waybar":
                    continue
            os.kill(int(entry), sig)
            sent = True
        except OSError:
            continue
    return sent
