"""Turning a settings change into a desktop that looks different.

One entry point, `apply()`, runs the whole chain: settings → palette →
tokens → generated files → live reload. Everything that changes the
desktop's appearance goes through here, so there is exactly one place
where "did that actually take effect?" can be answered.

Reloading is best-effort by design. A missing Waybar is not a reason to
refuse to regenerate Quickshell's theme.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
from dataclasses import dataclass, field
from typing import Any, Iterable

from . import environment, hyprland, jsonc, palette as palette_module, paths
from . import render, settings as settings_module, theme as theme_module


@dataclass
class ApplyResult:
    written: list[str] = field(default_factory=list)
    reloaded: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    mode: str = "dark"
    accent: str = ""
    palette_source: str = "fallback"


def _search_paths(*relative: str) -> list[str]:
    """Look in the installed data directory, then the source checkout."""
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(here))
    return [
        os.path.join(str(paths.DATA_DIR), *relative),
        os.path.join(repo_root, *relative),
    ]


def _first_existing(candidates: Iterable[str]) -> str | None:
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return None


def load_catalog() -> dict[str, Any]:
    path = _first_existing(
        _search_paths("keybinds.catalog.json")
        + _search_paths("config", "system", "keybinds.catalog.json")
    )
    if path is None:
        return {"binds": [], "mouseBinds": []}
    with open(path, "r", encoding="utf-8") as handle:
        import json

        return json.load(handle)


def load_waybar_modules() -> dict[str, Any]:
    path = _first_existing(
        _search_paths("waybar-modules.jsonc")
        + _search_paths("config", "waybar", "modules.jsonc")
        + [str(paths.XDG_CONFIG_HOME / "waybar" / "modules.jsonc")]
    )
    if path is None:
        return {}
    try:
        return jsonc.load_file(path)
    except (OSError, ValueError):
        return {}


def current_wallpaper(settings: dict[str, Any]) -> str | None:
    """The wallpaper the palette should be derived from.

    Rotation writes the active path to state, so the palette follows the
    picture actually on screen rather than the one named in settings.
    """
    state_file = paths.STATE_DIR / "wallpaper"
    if state_file.is_file():
        try:
            candidate = state_file.read_text(encoding="utf-8").strip()
        except OSError:
            candidate = ""
        if candidate and os.path.isfile(os.path.expanduser(candidate)):
            return os.path.expanduser(candidate)

    configured = str(settings.get("wallpaper", {}).get("path", "")).strip()
    if configured:
        expanded = os.path.expanduser(configured)
        if os.path.isfile(expanded):
            return expanded
    return None


def build(settings: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Resolve settings into `(settings, tokens)` without writing anything."""
    settings = settings or settings_module.load()
    wallpaper_settings = settings.get("wallpaper", {})
    appearance = settings.get("appearance", {})

    use_wallpaper = bool(
        wallpaper_settings.get("deriveColors", True)
        and appearance.get("accentSource", "wallpaper") == "wallpaper"
    )
    swatch_palette = palette_module.derive(
        current_wallpaper(settings),
        str(appearance.get("accentColor", "#0A84FF")),
        use_wallpaper=use_wallpaper,
    )
    return settings, theme_module.resolve(settings, swatch_palette)


def apply(
    *,
    reload: bool = True,
    outputs: Iterable[str] | None = None,
    settings: dict[str, Any] | None = None,
) -> ApplyResult:
    """Regenerate everything and tell the running desktop about it."""
    paths.ensure_dirs()
    result = ApplyResult()

    settings, tokens = build(settings)
    result.mode = tokens["mode"]
    result.accent = tokens["palette"]["accent"]
    result.palette_source = tokens["palette"]["source"]

    env_vars, env_notes = environment.build(settings)
    result.warnings.extend(
        note for note in env_notes if note.startswith(("No ", "An ", "More"))
    )

    try:
        result.written = render.write_all(
            tokens,
            settings,
            load_catalog(),
            load_waybar_modules(),
            env_vars,
            outputs=outputs,
        )
    except render.RenderError as exc:
        # A generated file that Hyprland would reject is worse than no
        # change at all, so nothing is written and the caller hears why.
        raise

    render.write_atomic(
        paths.PALETTE_JSON,
        render.render_theme_json(tokens["palette"]),
    )
    result.written.append(str(paths.PALETTE_JSON))

    if reload:
        result.reloaded, reload_warnings = reload_components()
        result.warnings.extend(reload_warnings)

    return result


def reload_components() -> tuple[list[str], list[str]]:
    """Ask each running component to pick up the new files.

    Quickshell is absent from this list on purpose: it watches
    `theme.json` with a FileView and reloads itself, which is both faster
    and avoids tearing down every window to change a colour.
    """
    reloaded: list[str] = []
    warnings: list[str] = []

    if hyprland.running():
        if hyprland.reload():
            reloaded.append("hyprland")
        else:
            warnings.append("hyprctl reload failed; run it by hand to see the error.")
        errors = hyprland.config_errors()
        if errors:
            warnings.append(
                "Hyprland reports configuration errors:\n  "
                + "\n  ".join(errors[:10])
            )

    if _signal_process("waybar", signal.SIGUSR2):
        reloaded.append("waybar")

    return reloaded, warnings


def _signal_process(name: str, sig: int) -> bool:
    """Signal every instance of a process by name, without pkill.

    `pkill` is not installed everywhere, and shelling out to it to send
    one signal is slower than reading /proc.
    """
    sent = False
    own_pid = os.getpid()
    try:
        entries = os.listdir("/proc")
    except OSError:
        entries = []

    for entry in entries:
        if not entry.isdigit():
            continue
        pid = int(entry)
        if pid == own_pid:
            continue
        try:
            with open(f"/proc/{pid}/comm", "r", encoding="utf-8") as handle:
                if handle.read().strip() != name:
                    continue
            os.kill(pid, sig)
            sent = True
        except (OSError, PermissionError):
            continue

    if not sent and shutil.which(name) is None:
        return False
    return sent


def restart_waybar() -> bool:
    """A full restart, for changes SIGUSR2 cannot pick up (module set)."""
    if shutil.which("waybar") is None:
        return False
    _signal_process("waybar", signal.SIGTERM)
    config = paths.GENERATED_DIR / "waybar-config.jsonc"
    style = paths.XDG_CONFIG_HOME / "waybar" / "style.css"
    try:
        subprocess.Popen(
            ["waybar", "-c", str(config), "-s", str(style)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError:
        return False
    return True
