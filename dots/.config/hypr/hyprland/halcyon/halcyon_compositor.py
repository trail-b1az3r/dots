"""Which Hyprland is running, or installed, and what it can do.

hyprland-plus gained its features over several builds, so "is this hyprland-plus" and "does it have Plus Tiles" are
separate questions. A hyprland-plus built before Plus Tiles still says "hyprland-plus" in its version line, and still
has mini windows and the superposition strip; it only lacks the plus:* options. compositor.lua answers the same
questions from inside the config.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess

UPDATE_HINT = "update it with: sudo hyprctl-lite install update"


def _run(argv: list[str], timeout: float = 5) -> str | None:
    if not shutil.which(argv[0]):
        return None
    try:
        out = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False,
                             stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout if out.returncode == 0 else None


def running() -> bool:
    return bool(shutil.which("hyprctl") and os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"))


def has_option(name: str) -> bool:
    text = _run(["hyprctl", "getoption", name, "-j"])
    if not text:
        return False
    try:
        data = json.loads(text)
    except ValueError:
        return False
    return isinstance(data, dict) and any(k in data for k in ("int", "float", "str", "custom", "data", "vec2"))


def is_plus_version(text: str | None) -> bool:
    """Every hyprland-plus build names itself in its version line: "hyprland-plus 0.56.2.p1 (Hyprland 0.56.2) ..."."""
    return bool(text) and "hyprland-plus" in text.lower()


def first_line(text: str | None) -> str:
    return (text or "").strip().splitlines()[0] if (text or "").strip() else ""


def detect() -> dict:
    """{running, plus, strips, tiles, version}. With Hyprland not running, the installed binary is asked instead,
    and strips and tiles are unknown (None)."""
    if running():
        version = _run(["hyprctl", "version"])
        plus = is_plus_version(version)
        tiles = plus and has_option("plus:enabled")
        strips = plus and (tiles or has_option("superposition:size"))
        return {"running": True, "plus": plus, "strips": strips, "tiles": tiles, "version": first_line(version)}
    binary = shutil.which("Hyprland") or shutil.which("hyprland")
    version = _run([binary, "--version"]) if binary else None
    return {"running": False, "plus": is_plus_version(version), "strips": None, "tiles": None,
            "version": first_line(version), "binary": binary}


def describe(info: dict) -> str:
    """One line for people: what is running and what it lacks."""
    if not info.get("version"):
        return "Hyprland was not found" if not info.get("running") else "Hyprland did not answer"
    if not info.get("plus"):
        return f"stock Hyprland ({info['version']}): the Plus features are off"
    if info.get("tiles") is False:
        return f"hyprland-plus, but a build from before Plus Tiles ({info['version']}): {UPDATE_HINT}"
    return f"hyprland-plus ({info['version']})"


if __name__ == "__main__":
    import sys
    info = detect()
    if sys.argv[1:] == ["--json"]:
        print(json.dumps(info))
    else:
        print(describe(info))
