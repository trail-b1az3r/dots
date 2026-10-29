#!/usr/bin/env python3
"""Alacritty as the terminal: `halcyon terminal`.

    halcyon terminal          which terminal Super + Return opens, and whether Alacritty is installed
    halcyon terminal login    once, at a login after Alacritty is installed: kitty's pins go to it (Hyprland runs this)

Super + Return opens the first of Alacritty, foot, kitty... that is installed. kitty's Ctrl+C copied instead of
interrupting whenever text was selected (copy_or_interrupt), which taps on a touchscreen or touchpad leave behind
easily; Alacritty's Ctrl+C always interrupts, and Ctrl+Shift+C copies. `login` moves kitty's place in the dock and
launcher pins to Alacritty, once, so pinning kitty again afterwards stays.
"""

from __future__ import annotations

import shutil
import sys

import halcyon_file_manager as fm

DONE = fm.STATE / "terminal-alacritty"
OLD_PINS = ("kitty",)
PIN = "Alacritty"   # Alacritty.desktop
ORDER = ("alacritty", "foot", "kitty", "wezterm", "konsole", "kgx", "uxterm", "xterm")


def alacritty_installed() -> bool:
    return bool(shutil.which("alacritty") and fm.desktop_file(PIN))


def first_installed() -> str:
    return next((t for t in ORDER if shutil.which(t)), "")


def login() -> int:
    if DONE.exists() or not alacritty_installed():
        return 0
    pins = fm.swap_pins(PIN, OLD_PINS)
    fm.STATE.mkdir(parents=True, exist_ok=True)
    DONE.write_text("done\n", encoding="utf-8")
    if pins:
        print(f"{pins} kitty pin(s) moved to Alacritty")
    return 0


def main(argv: list[str]) -> int:
    if argv[:1] == ["login"]:
        return login()
    if argv and argv[0] not in ("status",):
        print("usage: halcyon terminal [status | login]", file=sys.stderr)
        return 2
    print(f"Super + Return opens  {first_installed() or '(no terminal found)'}")
    print(f"Alacritty             {'installed' if alacritty_installed() else 'not installed: sudo pacman -S alacritty'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
