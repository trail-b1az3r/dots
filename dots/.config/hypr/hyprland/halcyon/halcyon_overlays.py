#!/usr/bin/env python3
"""On-screen display and screen annotation that follow Halcyon: `halcyon osd`, `halcyon annotate`.

    halcyon osd                       which volume/brightness popup is on, and whether Avizo is installed and running
    halcyon osd avizo | shell         use Avizo for the popups, or the shell's own
    halcyon osd test                  show a popup now
    halcyon annotate                  Wayscriber: installed, running, on at login
    halcyon annotate on | off         run Wayscriber's daemon at login (and now), or stop it
    halcyon annotate toggle           show or hide the drawing overlay (SUPER + SHIFT + D)
    halcyon overlays sync             write both tools' colours from the current theme (themes and wallpapers do this)

Avizo (https://github.com/heyjuvi/avizo) draws the volume, microphone and brightness popup. With it selected the
shell's own popup is switched off, the media keys call `halcyon-osd` after they change the level, and
~/.config/avizo/config.ini takes the theme's colours, shape and fonts.

Wayscriber (https://github.com/devmobasa/hyprmarker, called Hyprmarker before it was renamed) draws on the screen,
like ZoomIt: pen, shapes, text, a whiteboard. Its daemon starts at login and SUPER + SHIFT + D shows and hides it.
~/.config/wayscriber/config.toml takes the theme's colours for the pen palette and the overlay's panels.

Both config files carry a "halcyon-managed" line. A file without it is yours and is never touched.
"""

from __future__ import annotations

import argparse
import colorsys
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import halcyon_browsers as browsers

HERE = Path(__file__).resolve().parent
HOME = Path.home()
CONFIG = Path(os.environ.get("XDG_CONFIG_HOME") or HOME / ".config")
STATE = Path(os.environ.get("XDG_STATE_HOME") or HOME / ".local/state")

STATE_DIR = STATE / "halcyon"
SETTINGS = STATE_DIR / "overlays.json"
LUA = STATE_DIR / "overlays.lua"
AVIZO_FLAG = STATE_DIR / "osd-avizo"          # halcyon-osd shows a popup only while this exists
AVIZO_CONFIG = CONFIG / "avizo/config.ini"
WAYSCRIBER_CONFIG = CONFIG / "wayscriber/config.toml"
USER_THEMES = CONFIG / "halcyon/themes"

MARK = "halcyon-managed"
INI_MARK = f"; {MARK}: written from the active theme by `halcyon overlays sync`. Delete this line to keep your own settings."
TOML_MARK = f"# {MARK}: written from the active theme by `halcyon overlays sync`. Delete this line to keep your own settings."

OSD_PROVIDERS = ("shell", "avizo")
DEFAULTS = {"osd": "shell", "annotate": True}


# --- settings ---------------------------------------------------------------------------------------------------

def load_settings() -> dict:
    try:
        data = json.loads(SETTINGS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    settings = dict(DEFAULTS)
    if isinstance(data, dict):
        if data.get("osd") in OSD_PROVIDERS:
            settings["osd"] = data["osd"]
        if isinstance(data.get("annotate"), bool):
            settings["annotate"] = data["annotate"]
    return settings


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def save_settings(settings: dict) -> None:
    """The settings file, the Lua file Hyprland reads at login, and the flag halcyon-osd checks."""
    write_atomic(SETTINGS, json.dumps(settings, indent=2) + "\n")
    write_atomic(LUA, "-- Written by halcyon (osd, annotate). Change it with `halcyon osd` and `halcyon annotate`.\n"
                      f"HALCYON_OSD = \"{settings['osd']}\"\n"
                      f"HALCYON_ANNOTATE = {'true' if settings['annotate'] else 'false'}\n")
    if settings["osd"] == "avizo":
        AVIZO_FLAG.touch()
    else:
        AVIZO_FLAG.unlink(missing_ok=True)


# --- the theme ----------------------------------------------------------------------------------------------------

def theme_file(theme_id: str) -> dict:
    for folder in (HERE / "themes", USER_THEMES):
        try:
            data = json.loads((folder / f"{theme_id}.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict):
            return data
    return {}


def rounding() -> int:
    """The active theme's window rounding, which the popup and the panels borrow."""
    value = theme_file(browsers.active_theme()).get("hyprland", {}).get("rounding")
    return value if isinstance(value, int) and 0 <= value <= 60 else 12


def rgba_css(hex_colour: str, alpha: float) -> str:
    r, g, b = browsers.rgb(hex_colour)
    return f"rgba({r}, {g}, {b}, {alpha:g})"


def rgba_floats(hex_colour: str, alpha: float) -> str:
    r, g, b = browsers.rgb(hex_colour)
    return "[" + ", ".join(f"{channel / 255:.3f}" for channel in (r, g, b)) + f", {alpha:g}]"


# --- Avizo --------------------------------------------------------------------------------------------------------

def avizo_config(c: dict[str, str], radius: int) -> str:
    border_radius = min(32, max(6, round(radius * 1.5)))
    return "\n".join([
        INI_MARK,
        "[default]",
        "time = 1.4",
        "width = 220",
        "height = 208",
        "padding = 22",
        "x-offset = 0.5",
        "y-offset = 0.82",
        f"border-radius = {border_radius}",
        "border-width = 1",
        "block-height = 9",
        "block-spacing = 3",
        "block-count = 16",
        "fade-in = 0.16",
        "fade-out = 0.35",
        f"background = {rgba_css(c['surface_container'], 0.9)}",
        f"border-color = {rgba_css(c['outline_variant'], 0.7)}",
        f"bar-fg-color = {rgba_css(c['primary'], 1)}",
        f"bar-bg-color = {rgba_css(c['surface_container_highest'], 0.8)}",
        "",
    ])


# --- Wayscriber ---------------------------------------------------------------------------------------------------

# The pen palette: the usual pen colours, each leaning a quarter of the way to the theme's primary so they sit in
# the theme without turning into one colour, after the theme's own accent and its tertiary.
PEN_COLOURS = [("Red", "#F5333F"), ("Green", "#2EC27E"), ("Blue", "#3584E4"), ("Yellow", "#F6D32D"),
               ("Orange", "#FF7800"), ("Pink", "#C061CB"), ("Cyan", "#00D8E8")]


def pen_palette(c: dict[str, str]) -> list[tuple[str, str]]:
    palette = [("Accent", c["primary"]), ("Tertiary", c["tertiary"])]
    palette += [(name, browsers.mix(colour, c["primary"], 0.25)) for name, colour in PEN_COLOURS]
    palette += [("White", "#FFFFFF"), ("Black", browsers.mix(c["background"], "#000000", 0.5)),
                ("Gray", browsers.mix(c["outline"], c["background"], 0.2))]
    return palette


def wayscriber_config(c: dict[str, str]) -> str:
    lines = [
        TOML_MARK,
        "[drawing]",
        f'default_color = "{c["primary"]}"',
        "",
    ]
    for label, colour in pen_palette(c):
        lines += ["[[drawing.quick_colors]]", f'label = "{label}"', f'color = "{colour}"', ""]
    lines += [
        "[ui.status_bar_style]",
        f"bg_color = {rgba_floats(c['surface_container'], 0.92)}",
        f"text_color = {rgba_floats(c['on_surface'], 1)}",
        "",
        "[ui.help_overlay_style]",
        f"bg_color = {rgba_floats(c['surface_container_low'], 0.97)}",
        f"border_color = {rgba_floats(c['outline_variant'], 0.9)}",
        f"text_color = {rgba_floats(c['on_surface'], 1)}",
        "",
    ]
    return "\n".join(lines)


# --- writing the files -----------------------------------------------------------------------------------------

def is_ours(path: Path, mark_line: str) -> bool:
    """A file Halcyon may write: not there yet, or one it wrote (its first line says so)."""
    try:
        first = path.read_text(encoding="utf-8").splitlines()[0]
    except (OSError, IndexError):
        return not path.exists() or path.stat().st_size == 0
    return MARK in first


def sync(quiet: bool = False) -> dict:
    """Write the configs of the tools that are installed. Returns what happened to each."""
    colours = browsers.load_colors()
    result: dict[str, str] = {}
    for name, binary, path, text, mark in (
        ("avizo", "avizo-client", AVIZO_CONFIG, lambda: avizo_config(colours, rounding()), INI_MARK),
        ("wayscriber", "wayscriber", WAYSCRIBER_CONFIG, lambda: wayscriber_config(colours), TOML_MARK),
    ):
        if not shutil.which(binary):
            result[name] = "not installed"
        elif not is_ours(path, mark):
            result[name] = f"{path} is yours (no {MARK} line), left alone"
        else:
            write_atomic(path, text())
            result[name] = f"wrote {path}"
    if not quiet:
        for name, what in result.items():
            print(f"{name:11s} {what}")
    return result


# --- processes ------------------------------------------------------------------------------------------------------

def tell(message: str) -> None:
    """Print it, and as a notification when there is no terminal to read it on (a key press)."""
    print(message, file=sys.stderr)
    if not sys.stderr.isatty() and shutil.which("notify-send"):
        subprocess.run(["notify-send", "-a", "Halcyon", message], check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def running(name: str) -> bool:
    try:
        return subprocess.run(["pgrep", "-x", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                              check=False).returncode == 0
    except OSError:
        return False


def start_detached(command: list[str]) -> bool:
    try:
        subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
        return True
    except OSError:
        return False


def stop(name: str) -> None:
    try:
        subprocess.run(["pkill", "-x", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    except OSError:
        pass


def reload_hyprland() -> None:
    if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE") and shutil.which("hyprctl"):
        subprocess.run(["hyprctl", "reload"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


def ensure_avizo() -> bool:
    if running("avizo-service"):
        return True
    return bool(shutil.which("avizo-service")) and start_detached(["avizo-service"])


def ensure_wayscriber() -> bool:
    if running("wayscriber"):
        return True
    if not shutil.which("wayscriber"):
        return False
    started = start_detached(["wayscriber", "--daemon"])
    for _ in range(20):  # the daemon takes a moment to listen
        if running("wayscriber"):
            break
        time.sleep(0.1)
    return started


# --- commands -------------------------------------------------------------------------------------------------------

def osd_status() -> dict:
    settings = load_settings()
    return {
        "provider": settings["osd"],
        "avizo_installed": bool(shutil.which("avizo-service")) and bool(shutil.which("avizo-client")),
        "avizo_running": running("avizo-service"),
        "avizo_config": "managed" if AVIZO_CONFIG.exists() and is_ours(AVIZO_CONFIG, INI_MARK)
        else ("yours" if AVIZO_CONFIG.exists() else "none"),
    }


def annotate_status() -> dict:
    settings = load_settings()
    return {
        "installed": bool(shutil.which("wayscriber")),
        "running": running("wayscriber"),
        "at_login": settings["annotate"],
        "config": "managed" if WAYSCRIBER_CONFIG.exists() and is_ours(WAYSCRIBER_CONFIG, TOML_MARK)
        else ("yours" if WAYSCRIBER_CONFIG.exists() else "none"),
    }


def cmd_osd(args: argparse.Namespace) -> int:
    action = args.action
    if action in OSD_PROVIDERS:
        if action == "avizo" and not (shutil.which("avizo-service") and shutil.which("avizo-client")):
            print("Avizo is not installed. Install it first (Arch: `yay -S avizo`), then run `halcyon osd avizo`.",
                  file=sys.stderr)
            return 1
        settings = load_settings()
        settings["osd"] = action
        save_settings(settings)
        browsers.set_shell_option("osd.provider", action)
        if action == "avizo":
            sync(quiet=True)
            ensure_avizo()
        else:
            stop("avizo-service")
        reload_hyprland()
        print(f"volume and brightness popups: {action}")
        return 0
    if action == "test":
        if not shutil.which("avizo-client"):
            print("Avizo is not installed.", file=sys.stderr)
            return 1
        ensure_avizo()
        time.sleep(0.2)
        return subprocess.run(["avizo-client", "--image-resource=volume_high", "--progress=0.62"],
                              check=False).returncode
    status = osd_status()
    if args.json:
        print(json.dumps(status, indent=2))
        return 0
    print(f"popups   {status['provider']}" + ("" if status["provider"] == "shell" else " (Avizo)"))
    print(f"avizo    {'installed' if status['avizo_installed'] else 'not installed'}"
          + (", running" if status["avizo_running"] else ""))
    print(f"config   {status['avizo_config']}")
    return 0


def cmd_annotate(args: argparse.Namespace) -> int:
    action = args.action
    if action in ("on", "off"):
        settings = load_settings()
        settings["annotate"] = action == "on"
        save_settings(settings)
        browsers.set_shell_option("halcyon.annotate.enable", action == "on")
        if action == "on":
            sync(quiet=True)
            if not ensure_wayscriber():
                print("Wayscriber is not installed (Arch: `yay -S wayscriber-bin`). It will start at login once it is.",
                      file=sys.stderr)
        else:
            stop("wayscriber")
        reload_hyprland()
        print(f"drawing overlay at login: {action}")
        return 0
    if action == "toggle":
        if not ensure_wayscriber():
            tell("Wayscriber is not installed (Arch: yay -S wayscriber-bin).")
            return 1
        return subprocess.run(["wayscriber", "--daemon-toggle"], check=False).returncode
    status = annotate_status()
    if args.json:
        print(json.dumps(status, indent=2))
        return 0
    print(f"wayscriber  {'installed' if status['installed'] else 'not installed'}"
          + (", running" if status["running"] else ""))
    print(f"at login    {'on' if status['at_login'] else 'off'}")
    print(f"config      {status['config']}")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="halcyon", description="On-screen display and screen annotation.")
    sub = parser.add_subparsers(dest="command", required=True)

    osd = sub.add_parser("osd", help="the volume and brightness popup")
    osd.add_argument("action", nargs="?", choices=[*OSD_PROVIDERS, "test", "status"], default="status")
    osd.add_argument("--json", action="store_true")
    osd.set_defaults(run=cmd_osd)

    annotate = sub.add_parser("annotate", help="draw on the screen (Wayscriber)")
    annotate.add_argument("action", nargs="?", choices=["on", "off", "toggle", "status"], default="status")
    annotate.add_argument("--json", action="store_true")
    annotate.set_defaults(run=cmd_annotate)

    overlays = sub.add_parser("overlays", help="both tools together")
    overlays.add_argument("action", choices=["sync"])
    overlays.add_argument("--quiet", action="store_true")
    overlays.set_defaults(run=lambda args: (sync(args.quiet), 0)[1])

    args = parser.parse_args(argv)
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
