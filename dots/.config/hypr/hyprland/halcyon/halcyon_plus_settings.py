#!/usr/bin/env python3
"""Plus Tiles settings from Settings > Halcyon, written where Hyprland loads them.

    halcyon plus                    the settings, as Hyprland will get them
    halcyon plus apply              write them to $XDG_STATE_HOME/halcyon/plus.lua and reload Hyprland
    halcyon plus status             JSON for the Settings page: is hyprland-plus running, which files are in use
    halcyon plus edit rules|keys    copy app_rules.lua or plus_keys.lua to ~/.config/hypr/custom (if it is not
                                    there yet) and open the copy

The settings are stored under `halcyon.plus` in ~/.config/illogical-impulse/config.json. The written file is
loaded after hyprland/halcyon/plus.lua and before ~/.config/hypr/custom, so anything you set there still wins.
On stock Hyprland the file does nothing.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOME = Path.home()
CONFIG = Path(os.environ.get("XDG_CONFIG_HOME") or HOME / ".config")
STATE = Path(os.environ.get("XDG_STATE_HOME") or HOME / ".local/state")
SHELL_CONFIG = CONFIG / "illogical-impulse/config.json"
PLUS_LUA = STATE / "halcyon/plus.lua"
CUSTOM = HOME / ".config/hypr/custom"
EDITABLE = {"rules": "app_rules.lua", "keys": "plus_keys.lua"}

# Settings key -> (Lua path under hl.config, kind, default, low, high). The defaults match plus.lua.
SETTINGS = {
    "allTiled": ("plus.all_tiled", "bool", False, None, None),
    "editPreview": ("plus.edit_preview", "bool", True, None, None),
    "autoRestore": ("plus.auto_restore", "bool", True, None, None),
    "focusPreview": ("plus.focus_preview", "bool", False, None, None),
    "step": ("plus.step", "int", 40, 2, 400),
    "stepFine": ("plus.step_fine", "int", 10, 1, 200),
    "stepCoarse": ("plus.step_coarse", "int", 160, 4, 1000),
    "minWidth": ("plus.min_width", "int", 120, 20, 2000),
    "minHeight": ("plus.min_height", "int", 90, 20, 2000),
    "feedback": ("plus.feedback.enabled", "bool", True, None, None),
    "feedbackDuration": ("plus.feedback.duration", "int", 450, 0, 3000),
}


def resolve(stored: object) -> tuple[dict[str, object], list[str]]:
    """The settings to use, and a note for each stored value that was missing, wrong or out of order."""
    stored = stored if isinstance(stored, dict) else {}
    values: dict[str, object] = {}
    notes: list[str] = []
    for key, (_path, kind, default, low, high) in SETTINGS.items():
        value = stored.get(key, default)
        if kind == "bool":
            if not isinstance(value, bool):
                notes.append(f"{key} is not true or false; using {str(default).lower()}")
                value = default
        else:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                notes.append(f"{key} is not a number; using {default}")
                value = default
            value = int(round(value))
            if not low <= value <= high:
                clamped = min(max(value, low), high)
                notes.append(f"{key} {value} is outside {low}-{high}; using {clamped}")
                value = clamped
        values[key] = value
    # fine <= normal <= coarse, so the modifier keys always mean smaller and bigger steps
    if values["stepFine"] > values["step"]:
        notes.append(f"the fine step ({values['stepFine']}) is bigger than the normal step; using {values['step']}")
        values["stepFine"] = values["step"]
    if values["stepCoarse"] < values["step"]:
        notes.append(f"the coarse step ({values['stepCoarse']}) is smaller than the normal step; using {values['step']}")
        values["stepCoarse"] = values["step"]
    return values, notes


def lua_value(value: object) -> str:
    return str(value).lower() if isinstance(value, bool) else str(value)


def render(values: dict[str, object]) -> str:
    """The Lua file. Nested tables are written in SETTINGS order, so the output is stable."""
    tree: dict = {}
    for key, (path, *_rest) in SETTINGS.items():
        node = tree
        parts = path.split(".")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = values[key]

    def table(node: dict, indent: int) -> list[str]:
        pad = "    " * indent
        lines = []
        for name, value in node.items():
            if isinstance(value, dict):
                lines.append(f"{pad}{name} = {{")
                lines += table(value, indent + 1)
                lines.append(f"{pad}}},")
            else:
                lines.append(f"{pad}{name} = {lua_value(value)},")
        return lines

    body = "\n".join(table(tree, 2))
    return ("-- Written by `halcyon plus apply` from Settings > Halcyon > Plus Tiles. Do not edit: it is rewritten\n"
            "-- when the settings change. ~/.config/hypr/custom is loaded after this, so set things there instead.\n"
            "if hl.dsp and hl.dsp.plus then\n"
            "    hl.config({\n"
            f"{body}\n"
            "    })\n"
            "end\n")


def read_settings() -> object:
    try:
        data = json.loads(SHELL_CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return (data.get("halcyon") or {}).get("plus") if isinstance(data, dict) else {}


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def hyprland_running() -> bool:
    return bool(shutil.which("hyprctl") and os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"))


def plus_running() -> dict:
    """What the running compositor can do: see halcyon_compositor.py. An older hyprland-plus is still hyprland-plus."""
    import halcyon_compositor
    return halcyon_compositor.detect()


def custom_copy(which: str) -> Path:
    """Your copy of app_rules.lua or plus_keys.lua, made from Halcyon's if you do not have one yet."""
    name = EDITABLE[which]
    target = CUSTOM / name
    if not target.exists():
        CUSTOM.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(HERE / name, target)
    return target


def main(argv: list[str]) -> int:
    if argv and argv[0] in ("-h", "--help", "help"):
        print(__doc__.strip())
        return 0
    if not argv or argv == ["show"]:
        values, notes = resolve(read_settings())
        for key, (path, *_rest) in SETTINGS.items():
            print(f"{path.replace('.', ':'):24} {lua_value(values[key])}")
        for note in notes:
            print(f"note: {note}", file=sys.stderr)
        return 0
    if argv == ["apply"]:
        values, notes = resolve(read_settings())
        write_atomic(PLUS_LUA, render(values))
        for note in notes:
            print(f"note: {note}", file=sys.stderr)
        if hyprland_running():
            subprocess.run(["hyprctl", "reload"], stdout=subprocess.DEVNULL, check=False)
        print(f"wrote {PLUS_LUA}")
        return 0
    if argv == ["status"]:
        info = plus_running()
        print(json.dumps({
            "running": hyprland_running(),
            "plus": bool(info.get("plus")),
            # False: a hyprland-plus from before Plus Tiles, which needs updating for these settings
            "tiles": bool(info.get("tiles")) if info.get("running") else None,
            "version": info.get("version", ""),
            "file": str(PLUS_LUA),
            "applied": PLUS_LUA.exists(),
            "customRules": (CUSTOM / EDITABLE["rules"]).exists(),
            "customKeys": (CUSTOM / EDITABLE["keys"]).exists(),
        }))
        return 0
    if len(argv) == 2 and argv[0] == "edit" and argv[1] in EDITABLE:
        path = custom_copy(argv[1])
        print(path)
        if shutil.which("xdg-open"):
            subprocess.Popen(["xdg-open", str(path)], start_new_session=True,
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            print(f"xdg-open not found. Open {path} in your editor", file=sys.stderr)
        return 0
    print("usage: halcyon plus [show|apply|status|edit rules|edit keys]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
