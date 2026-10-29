#!/usr/bin/env python3
"""Loaf as the file manager: `halcyon files`.

    halcyon files            which file manager opens folders, and whether Loaf is installed
    halcyon files login      once, at a login after Loaf is installed: make it the default (Hyprland runs this)
    halcyon files use loaf|dolphin|...   make one the default now (any app with a .desktop file)

Loaf (https://github.com/m-uvex/loaf-fm, `loaf-fm` in the AUR) is Halcyon's file manager. Super + E opens the first
of Loaf, Dolphin, Nautilus... that is installed. `login` does the rest once Loaf is there: folders open in it
(xdg-mime, inode/directory), and Dolphin's place in the dock and launcher pins goes to it. It runs once, so a
choice you make afterwards (`halcyon files use dolphin`) stays.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
CONFIG = Path(os.environ.get("XDG_CONFIG_HOME") or HOME / ".config")
DATA = Path(os.environ.get("XDG_DATA_HOME") or HOME / ".local/share")
STATE = Path(os.environ.get("XDG_STATE_HOME") or HOME / ".local/state") / "halcyon"
DONE = STATE / "file-manager-loaf"
SHELL_CONFIG = CONFIG / "illogical-impulse/config.json"
APP_DIRS = [DATA / "applications", Path("/usr/local/share/applications"), Path("/usr/share/applications"),
            Path("/var/lib/flatpak/exports/share/applications")]
OLD_PINS = ("org.kde.dolphin", "dolphin")


def desktop_file(app: str) -> Path | None:
    for folder in APP_DIRS:
        if (folder / f"{app}.desktop").is_file():
            return folder / f"{app}.desktop"
    return None


def loaf_installed() -> bool:
    return bool(shutil.which("loaf") and desktop_file("loaf"))


def current() -> str:
    if not shutil.which("xdg-mime"):
        return ""
    done = subprocess.run(["xdg-mime", "query", "default", "inode/directory"], capture_output=True, text=True, check=False)
    return done.stdout.strip()


def set_default(app: str) -> bool:
    if not shutil.which("xdg-mime") or not desktop_file(app):
        return False
    return subprocess.run(["xdg-mime", "default", f"{app}.desktop", "inode/directory"], check=False).returncode == 0


def swap_pins(new: str, old: tuple[str, ...] = OLD_PINS) -> int:
    """The `old` app's pins (dock and launcher; Dolphin's by default) go to `new`, in place. Returns how many changed."""
    try:
        data = json.loads(SHELL_CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0
    changed = 0
    for section in ("dock", "launcher"):
        pins = (data.get(section) or {}).get("pinnedApps")
        if not isinstance(pins, list):
            continue
        swapped = []
        for pin in pins:
            if pin in old and new not in pins:
                swapped.append(new)
                changed += 1
            else:
                swapped.append(pin)
        data[section]["pinnedApps"] = swapped
    if changed:
        tmp = SHELL_CONFIG.with_name(SHELL_CONFIG.name + ".tmp")
        tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, SHELL_CONFIG)
    return changed


def login() -> int:
    if DONE.exists() or not loaf_installed():
        return 0
    set_default("loaf")
    pins = swap_pins("loaf")
    STATE.mkdir(parents=True, exist_ok=True)
    DONE.write_text("done\n", encoding="utf-8")
    print(f"Loaf opens folders now{f'; {pins} pin(s) moved to it' if pins else ''}")
    return 0


def main(argv: list[str]) -> int:
    if argv[:1] == ["login"]:
        return login()
    if len(argv) == 2 and argv[0] == "use":
        if not set_default(argv[1]):
            print(f"halcyon files: no {argv[1]}.desktop (or no xdg-mime)", file=sys.stderr)
            return 1
        STATE.mkdir(parents=True, exist_ok=True)
        DONE.write_text("chosen\n", encoding="utf-8")
        print(f"folders open in {argv[1]}")
        return 0
    if argv and argv[0] not in ("status",):
        print("usage: halcyon files [status | login | use APP]", file=sys.stderr)
        return 2
    print(f"folders open in  {current() or '(not set)'}")
    print(f"Loaf             {'installed' if loaf_installed() else 'not installed: yay -S loaf-fm'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
