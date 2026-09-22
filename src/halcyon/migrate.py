"""Bringing an older settings file forward.

Halcyon's settings are the user's overrides, not a full document, so a
migration only has to touch keys they actually set. That keeps each step
small and makes the whole chain safe to re-run: migrating an already
migrated file is a no-op.

Two rules shape this module:

* **Never discard what you cannot interpret.** A key this build does not
  recognise is left exactly where it is. Someone may be running a newer
  Halcyon tomorrow, and a setting silently deleted today is one they
  will have to find and set again.
* **Back up first.** `run()` writes the pre-migration file next to the
  backups the installer makes, before anything is changed, and names the
  copy after the version it came from.

Each step is a function from one override document to the next, keyed by
the version it upgrades *from*. Adding a schema version means adding one
function and one entry to `STEPS`.
"""

from __future__ import annotations

import copy
import json
import os
import shutil
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from . import SETTINGS_SCHEMA_VERSION, paths

Step = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass
class Result:
    migrated: bool = False
    from_version: int = 0
    to_version: int = 0
    backup: str | None = None
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "migrated": self.migrated,
            "fromVersion": self.from_version,
            "toVersion": self.to_version,
            "backup": self.backup,
            "notes": list(self.notes),
        }


# ── Version 1 → 2 ──────────────────────────────────────────────────────

#: Waybar module names, and what they became in the Ultra Bar. Waybar's
#: own ids described its module system ("custom/menu" was a shell
#: command; "pulseaudio#microphone" was a second instance of one module),
#: and none of them mean anything to a bar we wrote.
_WAYBAR_TO_ULTRA: dict[str, str | None] = {
    "custom/menu": "launcher",
    "custom/launcher": "launcher",
    "hyprland/workspaces": "workspaces",
    "hyprland/window": "activeWindow",
    "hyprland/submap": None,
    "clock": "clock",
    "mpris": "media",
    "tray": "tray",
    "cpu": "cpu",
    "memory": "memory",
    "temperature": "temperature",
    "disk": None,
    "load": None,
    "custom/gpu": "gpu",
    "network": "network",
    "bluetooth": "bluetooth",
    "pulseaudio": "audio",
    "pulseaudio#microphone": "microphone",
    "wireplumber": "audio",
    "battery": "battery",
    "backlight": None,
    "custom/powermode": "powerProfile",
    "power-profiles-daemon": "powerProfile",
    "custom/notifications": "notifications",
    "custom/control": "systemMenu",
    "custom/assistant": "assistant",
    "custom/hypernix": "hypernix",
    "custom/clipboard": "clipboard",
    "privacy": None,
    "idle_inhibitor": None,
    "keyboard-state": None,
    "user": None,
}


def _migrate_bar_section(
    section: list[Any], notes: list[str], side: str
) -> list[Any]:
    out: list[Any] = []
    for name in section:
        if not isinstance(name, str):
            out.append(name)
            continue
        if name in _WAYBAR_TO_ULTRA:
            replacement = _WAYBAR_TO_ULTRA[name]
            if replacement is None:
                notes.append(
                    f"bar.{side}: dropped {name!r} — the Ultra Bar has no "
                    "equivalent module"
                )
                continue
            if replacement in out:
                # Two Waybar ids can map to one Ultra Bar module.
                notes.append(
                    f"bar.{side}: {name!r} merged into {replacement!r}"
                )
                continue
            notes.append(f"bar.{side}: {name!r} → {replacement!r}")
            out.append(replacement)
        else:
            # Not a name we know. It may be an Ultra Bar id already, or
            # something from a future version; either way, keep it.
            out.append(name)
    return out


def _step_1_to_2(overrides: dict[str, Any]) -> dict[str, Any]:
    """Ultra Bar replaces Waybar, so bar layouts change names."""
    notes: list[str] = overrides.setdefault("_migrationNotes", [])
    bar = overrides.get("bar")
    if isinstance(bar, dict):
        for side in ("left", "center", "right"):
            section = bar.get(side)
            if isinstance(section, list):
                bar[side] = _migrate_bar_section(section, notes, side)

        # Someone who had a bar at all was using Waybar, and may want it
        # kept as the fallback while they try the new one. But choosing
        # for them is worse than the default, so only record the note.
        if any(isinstance(bar.get(s), list) for s in ("left", "center", "right")):
            notes.append(
                "The bar is now Halcyon's own. Set bar.fallbackBar to "
                '"waybar" if you want Waybar to keep running as well.'
            )
    return overrides


STEPS: dict[int, Step] = {
    1: _step_1_to_2,
}


# ── Running ────────────────────────────────────────────────────────────


def needs_migration(overrides: dict[str, Any] | None = None) -> bool:
    if overrides is None:
        overrides = _read_overrides()
    version = overrides.get("version", 1)
    if not isinstance(version, int):
        return False
    return version < SETTINGS_SCHEMA_VERSION


def _read_overrides() -> dict[str, Any]:
    try:
        with open(paths.SETTINGS_FILE, "r", encoding="utf-8") as handle:
            loaded = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _backup(from_version: int) -> str | None:
    """Copy the current settings file aside before changing it."""
    source = str(paths.SETTINGS_FILE)
    if not os.path.isfile(source):
        return None
    directory = paths.STATE_DIR / "migrations"
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None
    stamp = time.strftime("%Y%m%d-%H%M%S")
    target = str(directory / f"settings-v{from_version}-{stamp}.json")
    try:
        shutil.copy2(source, target)
    except OSError:
        return None
    return target


def migrate(overrides: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Apply every step needed, in order. Pure: no files are touched."""
    working = copy.deepcopy(overrides)
    version = working.get("version", 1)
    if not isinstance(version, int):
        version = 1

    while version < SETTINGS_SCHEMA_VERSION:
        step = STEPS.get(version)
        if step is None:
            # No step for this version: stop rather than claim the file
            # is current when nothing was done to it.
            break
        working = step(working)
        version += 1
        working["version"] = version

    notes = working.pop("_migrationNotes", [])
    return working, list(notes)


def run(*, dry_run: bool = False) -> Result:
    """Migrate the user's settings file in place, backing it up first."""
    overrides = _read_overrides()

    # No settings file, or an empty one, is not an old settings file.
    # Every key falls back to a default, and reporting a migration here
    # would be announcing work that did not happen.
    if not os.path.isfile(paths.SETTINGS_FILE) or not overrides:
        return Result(
            migrated=False,
            from_version=SETTINGS_SCHEMA_VERSION,
            to_version=SETTINGS_SCHEMA_VERSION,
        )

    from_version = overrides.get("version", 1)
    if not isinstance(from_version, int):
        from_version = 1

    if from_version >= SETTINGS_SCHEMA_VERSION:
        return Result(
            migrated=False,
            from_version=from_version,
            to_version=SETTINGS_SCHEMA_VERSION,
        )

    updated, notes = migrate(overrides)
    result = Result(
        migrated=True,
        from_version=from_version,
        to_version=updated.get("version", SETTINGS_SCHEMA_VERSION),
        notes=notes,
    )

    if dry_run:
        result.migrated = False
        result.notes.insert(0, "(dry run — nothing was written)")
        return result

    result.backup = _backup(from_version)

    from . import settings as settings_module

    settings_module.save(updated)
    return result
