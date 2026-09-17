"""The wallpaper system.

Supports whichever daemon is installed — swww (which can cross-fade and
handles animated formats) or hyprpaper — and falls back to a solid colour
drawn by Hyprland itself when neither is present, so a fresh install
never shows a black void.

Setting a wallpaper re-derives the palette, which is what makes the whole
desktop change colour with the picture.
"""

from __future__ import annotations

import os
import random
import shutil
import subprocess
import time
from typing import Any

from . import paths, settings as settings_module

IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".jxl", ".avif")

Result = tuple[bool, str]


def _have(name: str) -> bool:
    return shutil.which(name) is not None


def backend() -> str:
    if _have("swww"):
        return "swww"
    if _have("hyprpaper"):
        return "hyprpaper"
    return "none"


def _state_file() -> str:
    return str(paths.STATE_DIR / "wallpaper")


def current() -> str | None:
    try:
        value = open(_state_file(), encoding="utf-8").read().strip()
    except OSError:
        value = ""
    if value and os.path.isfile(value):
        return value
    configured = str(settings_module.load().get("wallpaper", {}).get("path", "")).strip()
    expanded = os.path.expanduser(configured)
    return expanded if configured and os.path.isfile(expanded) else None


def _record(path: str) -> None:
    paths.STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(_state_file(), "w", encoding="utf-8") as handle:
        handle.write(path)


def _ensure_swww_daemon() -> bool:
    try:
        done = subprocess.run(
            ["swww", "query"], capture_output=True, timeout=4, check=False
        )
        if done.returncode == 0:
            return True
        subprocess.Popen(
            ["swww-daemon"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        # swww-daemon needs a moment to bind before it will accept an image.
        for _ in range(20):
            time.sleep(0.1)
            done = subprocess.run(
                ["swww", "query"], capture_output=True, timeout=4, check=False
            )
            if done.returncode == 0:
                return True
    except (OSError, subprocess.TimeoutExpired):
        return False
    return False


def _apply_swww(path: str, settings: dict[str, Any], monitor: str | None) -> Result:
    if not _ensure_swww_daemon():
        return False, "swww-daemon would not start"
    motion = settings.get("motion", {})
    reduced = motion.get("reducedMotion") or settings.get("accessibility", {}).get(
        "reducedMotion"
    )
    argv = [
        "swww", "img", path,
        "--transition-type", "simple" if reduced else "grow",
        "--transition-duration", "0.4" if reduced else "1.1",
        "--transition-fps", "30" if reduced else "60",
        "--resize", {"fill": "crop", "fit": "fit", "stretch": "stretch"}.get(
            str(settings.get("wallpaper", {}).get("mode", "fill")), "crop"
        ),
    ]
    if monitor:
        argv += ["--outputs", monitor]
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    if done.returncode != 0:
        return False, done.stderr.strip() or "swww failed"
    return True, path


def _apply_hyprpaper(path: str, monitor: str | None) -> Result:
    if not _have("hyprctl"):
        return False, "hyprctl is needed to drive hyprpaper"
    try:
        subprocess.run(
            ["hyprctl", "hyprpaper", "preload", path],
            capture_output=True, timeout=20, check=False,
        )
        done = subprocess.run(
            ["hyprctl", "hyprpaper", "wallpaper", f"{monitor or ''},{path}"],
            capture_output=True, text=True, timeout=20, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    if done.returncode != 0:
        return False, done.stderr.strip() or "hyprpaper failed"
    return True, path


def set_wallpaper(path: str, *, monitor: str | None = None, rederive: bool = True) -> Result:
    """Show an image, remember it, and re-derive the palette from it."""
    expanded = os.path.abspath(os.path.expanduser(path))
    if not os.path.isfile(expanded):
        return False, f"No such image: {path}"

    settings = settings_module.load()
    chosen = backend()

    if chosen == "swww":
        ok, message = _apply_swww(expanded, settings, monitor)
    elif chosen == "hyprpaper":
        ok, message = _apply_hyprpaper(expanded, monitor)
    else:
        # No daemon: Hyprland's own background colour is the fallback, and
        # it is already driven by the palette, so the desktop still looks
        # deliberate rather than broken.
        ok, message = (
            False,
            "No wallpaper daemon is installed (swww or hyprpaper). "
            "Halcyon will use the palette's backdrop colour instead.",
        )

    if ok or chosen == "none":
        _record(expanded)
        if monitor is None:
            settings_module.set_value("wallpaper.path", expanded)
        if rederive:
            from . import pipeline

            pipeline.apply()

    return ok, message


def rotation_directory(settings: dict[str, Any] | None = None) -> str | None:
    settings = settings or settings_module.load()
    rotation = settings.get("wallpaper", {}).get("rotation", {})
    configured = str(rotation.get("directory", "")).strip()
    if configured:
        expanded = os.path.expanduser(configured)
        return expanded if os.path.isdir(expanded) else None
    for candidate in (str(paths.WALLPAPER_DIR), os.path.expanduser("~/Pictures/Wallpapers")):
        if os.path.isdir(candidate):
            return candidate
    return None


def library(settings: dict[str, Any] | None = None) -> list[str]:
    directory = rotation_directory(settings)
    if directory is None:
        return []
    found: list[str] = []
    for root, _dirs, files in os.walk(directory):
        for name in sorted(files):
            if name.lower().endswith(IMAGE_SUFFIXES):
                found.append(os.path.join(root, name))
    return found


def next_wallpaper() -> Result:
    settings = settings_module.load()
    images = library(settings)
    if not images:
        directory = rotation_directory(settings)
        return False, (
            f"No images found in {directory}"
            if directory
            else "No wallpaper folder is configured (Settings → Wallpaper)."
        )

    shuffle = bool(settings.get("wallpaper", {}).get("rotation", {}).get("shuffle", True))
    active = current()

    if shuffle and len(images) > 1:
        candidates = [image for image in images if image != active] or images
        chosen = random.choice(candidates)
    else:
        try:
            index = images.index(active) if active else -1
        except ValueError:
            index = -1
        chosen = images[(index + 1) % len(images)]

    return set_wallpaper(chosen)


def watch(stop_after: float | None = None) -> None:
    """Rotate on a timer. Sleeps between changes; never spins."""
    started = time.monotonic()
    while True:
        settings = settings_module.load()
        rotation = settings.get("wallpaper", {}).get("rotation", {})
        if not rotation.get("enabled"):
            # Disabled: check back in a minute rather than exiting, so the
            # unit does not need restarting when the user turns it on.
            time.sleep(60)
        else:
            next_wallpaper()
            time.sleep(max(60, int(rotation.get("intervalMinutes", 30)) * 60))
        if stop_after is not None and time.monotonic() - started >= stop_after:
            return
