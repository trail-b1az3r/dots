"""Where Halcyon keeps its files.

Everything is XDG-correct and overridable by environment variable, which
is what makes the test suite and `--dry-run` installs possible without
touching a real session.
"""

from __future__ import annotations

import os
from pathlib import Path


def _env_dir(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    return Path(value).expanduser() if value else default


HOME = Path.home()

XDG_CONFIG_HOME = _env_dir("XDG_CONFIG_HOME", HOME / ".config")
XDG_DATA_HOME = _env_dir("XDG_DATA_HOME", HOME / ".local" / "share")
XDG_STATE_HOME = _env_dir("XDG_STATE_HOME", HOME / ".local" / "state")
XDG_CACHE_HOME = _env_dir("XDG_CACHE_HOME", HOME / ".cache")

#: Everything the user may edit.
CONFIG_DIR = _env_dir("HALCYON_CONFIG_DIR", XDG_CONFIG_HOME / "halcyon")

#: Everything Halcyon generates. Safe to delete; regenerated on demand.
GENERATED_DIR = _env_dir("HALCYON_GENERATED_DIR", CONFIG_DIR / "generated")

#: Read-only payload shipped with the installation (presets, defaults).
DATA_DIR = _env_dir("HALCYON_DATA_DIR", XDG_DATA_HOME / "halcyon")

STATE_DIR = _env_dir("HALCYON_STATE_DIR", XDG_STATE_HOME / "halcyon")
CACHE_DIR = _env_dir("HALCYON_CACHE_DIR", XDG_CACHE_HOME / "halcyon")

SETTINGS_FILE = CONFIG_DIR / "settings.json"
DEFAULTS_FILE = DATA_DIR / "settings.default.json"

THEME_JSON = GENERATED_DIR / "theme.json"
PALETTE_JSON = GENERATED_DIR / "palette.json"
HYPR_THEME_LUA = GENERATED_DIR / "hypr-theme.lua"
HYPR_ANIM_LUA = GENERATED_DIR / "hypr-animations.lua"
WAYBAR_CSS = GENERATED_DIR / "waybar-colors.css"

PRESETS_DIR = DATA_DIR / "themes"
WALLPAPER_DIR = _env_dir("HALCYON_WALLPAPER_DIR", DATA_DIR / "wallpapers")

CONVERSATION_DIR = STATE_DIR / "assistant"
LOG_DIR = STATE_DIR / "log"


def runtime_dir() -> Path:
    """The per-session directory used for sockets.

    XDG_RUNTIME_DIR is the right place: user-private, on tmpfs, and
    cleared at logout so a stale socket cannot outlive a reboot.
    """
    value = os.environ.get("XDG_RUNTIME_DIR")
    if value and Path(value).is_dir():
        return Path(value)
    return Path(f"/tmp/halcyon-{os.getuid()}")  # noqa: S108 — last resort


ASSISTANT_SOCKET = runtime_dir() / "halcyon-assistant.sock"


def ensure_dirs() -> None:
    """Create the directories Halcyon writes to."""
    for directory in (
        CONFIG_DIR,
        GENERATED_DIR,
        STATE_DIR,
        CACHE_DIR,
        CONVERSATION_DIR,
        LOG_DIR,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    runtime_dir().mkdir(parents=True, exist_ok=True)
