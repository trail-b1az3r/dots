"""Minimise, hide and restore — macOS habits on a tiling compositor.

Hyprland has no concept of a minimised window, and inventing one badly
(moving windows off-screen, or to a workspace the user can wander into)
produces windows people cannot get back. Halcyon uses a special
workspace, which Hyprland already treats as "present but not shown", and
keeps an explicit stack in state so restore is deterministic rather than
"whatever comes back first".
"""

from __future__ import annotations

import json
import subprocess
from typing import Any

from . import hyprland, state

#: Special workspaces are Hyprland's own "off to one side" concept.
MINIMISED = "special:minimised"
_STACK = "minimised"


def _clients() -> list[dict[str, Any]]:
    if not hyprland.available():
        return []
    try:
        out = subprocess.run(
            ["hyprctl", "-j", "clients"],
            capture_output=True, text=True, timeout=4, check=False,
        ).stdout
        parsed = json.loads(out)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return []
    return parsed if isinstance(parsed, list) else []


def _active() -> dict[str, Any] | None:
    if not hyprland.available():
        return None
    try:
        out = subprocess.run(
            ["hyprctl", "-j", "activewindow"],
            capture_output=True, text=True, timeout=4, check=False,
        ).stdout
        parsed = json.loads(out)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None
    return parsed if isinstance(parsed, dict) and parsed.get("address") else None


def _stack() -> list[dict[str, Any]]:
    entries = state.read(_STACK, {"windows": []}).get("windows", [])
    return entries if isinstance(entries, list) else []


def _save_stack(entries: list[dict[str, Any]]) -> None:
    state.write(_STACK, {"windows": entries[-40:]}, refresh=False)


def _push(address: str, workspace: Any, title: str) -> None:
    entries = [item for item in _stack() if item.get("address") != address]
    entries.append({"address": address, "workspace": workspace, "title": title})
    _save_stack(entries)


def minimise(address: str | None = None) -> tuple[bool, str]:
    """Send a window to the minimised workspace, remembering where it was."""
    window = None
    if address:
        window = next((c for c in _clients() if c.get("address") == address), None)
    else:
        window = _active()
    if window is None:
        return False, "No window is focused."

    target = window["address"]
    workspace = (window.get("workspace") or {}).get("id")
    title = str(window.get("title") or window.get("class") or "window")

    ok = hyprland.dispatch(
        f'hl.dsp.window.move({{ window = "address:{target}", '
        f'workspace = "{MINIMISED}" }})'
    )
    if not ok:
        return False, "Hyprland would not move that window."

    _push(target, workspace, title)
    return True, f"Minimised {title}."


def hide_application() -> tuple[bool, str]:
    """Minimise every window of the focused application, as ⌘H does."""
    window = _active()
    if window is None:
        return False, "No window is focused."

    klass = str(window.get("class", ""))
    if not klass:
        return minimise()

    targets = [c for c in _clients() if str(c.get("class", "")) == klass]
    for client in targets:
        minimise(str(client.get("address")))
    return True, f"Hid {len(targets)} window(s) of {klass}."


def restore(address: str | None = None) -> tuple[bool, str]:
    """Bring back the most recently minimised window, or a named one."""
    entries = _stack()
    if not entries:
        return False, "Nothing has been minimised."

    if address:
        entry = next((item for item in entries if item.get("address") == address), None)
        if entry is None:
            return False, "That window is not in the minimised list."
    else:
        entry = entries[-1]

    target = str(entry["address"])
    live = {str(c.get("address")) for c in _clients()}
    if target not in live:
        # The window closed while minimised; drop it and try the next.
        _save_stack([item for item in entries if item.get("address") != target])
        return restore()

    workspace = entry.get("workspace")
    destination = workspace if isinstance(workspace, int) and workspace > 0 else None
    expression = (
        f'hl.dsp.window.move({{ window = "address:{target}", '
        f"workspace = {destination}, follow = true }})"
        if destination is not None
        else f'hl.dsp.window.move({{ window = "address:{target}", '
        'workspace = "e+0", follow = true })'
    )
    if not hyprland.dispatch(expression):
        return False, "Hyprland would not move that window back."

    hyprland.dispatch(f'hl.dsp.focus({{ window = "address:{target}" }})')
    _save_stack([item for item in entries if item.get("address") != target])
    return True, f"Restored {entry.get('title', 'window')}."


def minimised() -> list[dict[str, Any]]:
    """The minimised stack, filtered to windows that still exist."""
    live = {str(c.get("address")) for c in _clients()}
    entries = [item for item in _stack() if str(item.get("address")) in live]
    if len(entries) != len(_stack()):
        _save_stack(entries)
    return list(reversed(entries))
