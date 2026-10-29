#!/usr/bin/env python3
"""Lost windows: `halcyon lost`.

    halcyon lost          list windows that are off every screen (not ones put away on a hidden workspace)
    halcyon lost bring    bring them onto the current workspace, centred (the same as Super + Shift + W)

A window gets lost when the monitor it was on is unplugged, when a game moves itself, or when a drag goes too far.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys


def hyprctl(*args: str) -> str:
    return subprocess.run(["hyprctl", *args], capture_output=True, text=True, check=False).stdout


def on_a_monitor(window: dict, monitors: list[dict]) -> bool:
    (x, y), (w, h) = window.get("at", (0, 0)), window.get("size", (0, 0))
    for m in monitors:
        scale = m.get("scale") or 1
        mx, my = m.get("x", 0), m.get("y", 0)
        mw, mh = m.get("width", 0) / scale, m.get("height", 0) / scale
        if x < mx + mw and x + w > mx and y < my + mh and y + h > my:
            return True
    return False


def lost(clients: list[dict], monitors: list[dict]) -> list[dict]:
    found = []
    for c in clients:
        name = (c.get("workspace") or {}).get("name", "")
        if c.get("mapped") is False or name.startswith("special"):
            continue   # put away, not lost
        if not on_a_monitor(c, monitors):
            found.append(c)
    return found


def bring(found: list[dict]) -> None:
    """Onto the current workspace, floating and centred, one by one."""
    try:
        workspace = json.loads(hyprctl("activeworkspace", "-j") or "{}").get("id")
    except ValueError:
        workspace = None
    for c in found:
        address = c.get("address")
        steps = [f'hl.dsp.focus({{ window = "address:{address}" }})']
        if workspace is not None:
            steps.insert(0, f'hl.dsp.window.move({{ workspace = "{workspace}", follow = false, window = "address:{address}" }})')
        if not c.get("floating"):
            steps.append('hl.dsp.window.float({ action = "enable" })')
        steps.append("hl.dsp.window.center()")
        for step in steps:
            hyprctl("dispatch", step)


def main(argv: list[str]) -> int:
    if not shutil.which("hyprctl"):
        print("halcyon lost: hyprctl is not there (is Hyprland running?)", file=sys.stderr)
        return 1
    try:
        clients = json.loads(hyprctl("clients", "-j") or "[]")
        monitors = json.loads(hyprctl("monitors", "-j") or "[]")
    except ValueError:
        print("halcyon lost: Hyprland did not answer", file=sys.stderr)
        return 1
    found = lost(clients, monitors)
    if argv[:1] == ["bring"]:
        bring(found)
    if argv and argv[0] not in ("bring", "list"):
        print("usage: halcyon lost [list | bring]", file=sys.stderr)
        return 2
    if not found:
        print("no lost windows: every window is on a screen or put away")
        return 0
    for c in found:
        print(f"{c.get('address')}  {c.get('class') or '?':<24} at {c['at'][0]},{c['at'][1]}  {c.get('title', '')[:50]}")
    if argv[:1] == ["bring"]:
        print(f"{len(found)} brought back onto this workspace")
    else:
        print("Super + Shift + W (or halcyon lost bring) brings them back")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
