#!/usr/bin/env python3
"""halcyon oled: OLED burn-in care with hyproled (github.com/mklan/hyproled, BSD-3-Clause, in hyproled/).

    halcyon oled                     on or off, and how
    halcyon oled on [--pixels N] [--area x:y:w:h] [--monitor ID]
                                     dim N of every 2x2 pixels (1-3, default 1: 75% of the brightness kept), on the
                                     whole screen or an area (a bar), on one monitor (hyprctl monitors' id)
    halcyon oled off                 back to normal
    halcyon oled shift               move the dimmed pixel to the next of its 4 places (the timer does this every 15
                                     minutes, so no pixel stays lit all the time)

It stays on across logins and theme changes. While it is on, a theme's screen shader gives way to it: Hyprland runs
one screen shader at a time.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HYPROLED = HERE / "hyproled" / "hyproled"
STATE = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state") / "halcyon" / "oled.json"
TIMER = "halcyon-oled.timer"


def load() -> dict | None:
    try:
        data = json.loads(STATE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def hyproled_args(state: dict, shift: bool = False) -> list[str]:
    args = [str(HYPROLED), "-o", str(state.get("pixels", 1)), "-m", str(state.get("monitor", 0))]
    if state.get("area"):
        args += ["-a", state["area"]]
    if shift:
        args.append("-s")
    return args


def hyprland_running() -> bool:
    return bool(shutil.which("hyprctl")) and subprocess.run(
        ["hyprctl", "version"], capture_output=True, check=False).returncode == 0


def apply(state: dict, shift: bool = False) -> int:
    if not hyprland_running():
        return 0
    return subprocess.run(hyproled_args(state, shift), check=False).returncode


def systemctl(*args: str) -> None:
    if shutil.which("systemctl"):
        subprocess.run(["systemctl", "--user", *args], capture_output=True, check=False)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="halcyon oled", description="OLED burn-in care (hyproled)")
    parser.add_argument("action", nargs="?", default="status", choices=["status", "on", "off", "shift", "apply"])
    parser.add_argument("--pixels", type=int, default=None, help="pixels of every 2x2 block turned off (1-3)")
    parser.add_argument("--area", default=None, help="x:y:w:h, the part of the screen (default: all of it)")
    parser.add_argument("--monitor", type=int, default=None, help="the OLED monitor's id (hyprctl monitors)")
    a = parser.parse_args(argv)
    state = load()

    if a.action == "status":
        if not state:
            print("OLED care: off (halcyon oled on)")
        else:
            where = f"area {state['area']}" if state.get("area") else "the whole screen"
            print(f"OLED care: on, {state.get('pixels', 1)} of every 4 pixels dimmed on {where}, "
                  f"monitor {state.get('monitor', 0)}; the dimmed pixel moves every 15 minutes")
        return 0
    if a.action == "on":
        state = dict(state or {})
        if a.pixels is not None:
            if a.pixels not in (1, 2, 3):
                parser.error("--pixels is 1, 2 or 3")
            state["pixels"] = a.pixels
        if a.area is not None:
            if a.area and not re.fullmatch(r"\d+:\d+:\d+:\d+", a.area):
                parser.error("--area is x:y:w:h")
            state["area"] = a.area
        if a.monitor is not None:
            state["monitor"] = a.monitor
        state.setdefault("pixels", 1)
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(state) + "\n", encoding="utf-8")
        # The theme's screen shader steps aside (halcyon-theme reads the state file), then hyproled takes its place.
        theme = HERE / "halcyon-theme"
        subprocess.run([sys.executable, str(theme), "refresh"], capture_output=True, check=False)
        systemctl("enable", "--now", TIMER)
        code = apply(state)
        print("OLED care on." if code == 0 else "OLED care saved; it starts with Hyprland.")
        return 0
    if a.action == "off":
        try:
            STATE.unlink()
        except FileNotFoundError:
            pass
        systemctl("disable", "--now", TIMER)
        if hyprland_running():
            subprocess.run([str(HYPROLED), "off"], capture_output=True, check=False)
            # The theme's own screen shader, if it has one, comes back.
            subprocess.run([sys.executable, str(HERE / "halcyon-theme"), "refresh"], capture_output=True, check=False)
        print("OLED care off.")
        return 0
    if not state:
        return 0
    if a.action == "apply":
        # At login: the timer too (an install that turned it on before a reinstall, or a timer stopped by hand).
        systemctl("enable", "--now", TIMER)
    return apply(state, shift=a.action == "shift")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
