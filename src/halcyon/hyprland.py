"""Talking to Hyprland, and checking what we generate against it.

Hyprland's Lua API and option table move between releases, so nothing
here assumes a version. When a compositor is running, `hyprctl` is the
authority for its own options; when one is not — during installation, or
from a TTY — we fall back to the snapshot shipped in
`deps/hyprland-options.json` and say so.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from typing import Any

_SNAPSHOT_CACHE: dict[str, Any] | None = None


def available() -> bool:
    return shutil.which("hyprctl") is not None


def running() -> bool:
    return bool(os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"))


def _hyprctl(*args: str, timeout: float = 5.0) -> tuple[int, str, str]:
    if not available():
        return (127, "", "hyprctl is not installed")
    try:
        done = subprocess.run(
            ["hyprctl", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return (1, "", str(exc))
    return (done.returncode, done.stdout, done.stderr)


def version() -> str | None:
    """The installed Hyprland version, e.g. `0.56.2`."""
    code, out, _ = _hyprctl("version")
    if code != 0:
        return None
    match = re.search(r"v?(\d+\.\d+\.\d+)", out)
    return match.group(1) if match else None


def dispatch(expression: str) -> bool:
    """Run a dispatcher. `expression` is Lua, e.g. `hl.dsp.window.close()`.

    Hyprland 0.53 moved dispatchers into the Lua API; `hyprctl dispatch`
    accepts the Lua expression directly.
    """
    code, _, _ = _hyprctl("dispatch", expression)
    return code == 0


def reload() -> bool:
    code, _, _ = _hyprctl("reload")
    return code == 0


def notify(message: str, *, seconds: float = 4.0, icon: int = 1) -> bool:
    code, _, _ = _hyprctl(
        "notify", str(icon), str(int(seconds * 1000)), "0", message
    )
    return code == 0


def config_errors() -> list[str]:
    """Parsing errors Hyprland is currently reporting, if it is running."""
    if not running():
        return []
    code, out, _ = _hyprctl("configerrors")
    if code != 0:
        return []
    text = out.strip()
    if not text or text.lower().startswith("no errors"):
        return []
    return [line.strip() for line in text.splitlines() if line.strip()]


# ── Option table ───────────────────────────────────────────────────────


def _snapshot_path() -> str | None:
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(os.path.dirname(os.path.dirname(here)), "deps", "hyprland-options.json"),
        os.path.join(os.path.dirname(here), "hyprland-options.json"),
        os.path.expanduser("~/.local/share/halcyon/hyprland-options.json"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def _snapshot() -> dict[str, Any]:
    global _SNAPSHOT_CACHE
    if _SNAPSHOT_CACHE is None:
        path = _snapshot_path()
        if path is None:
            _SNAPSHOT_CACHE = {}
        else:
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    _SNAPSHOT_CACHE = json.load(handle).get("options", {})
            except (OSError, json.JSONDecodeError):
                _SNAPSHOT_CACHE = {}
    return _SNAPSHOT_CACHE or {}


def options() -> tuple[dict[str, Any], str]:
    """Return `(options, source)`.

    `source` is `"hyprctl"` when a live compositor answered and
    `"snapshot"` when we fell back, so callers can say which one they
    checked against instead of implying more certainty than they have.
    """
    if running():
        code, out, _ = _hyprctl("descriptions", "-j")
        if code == 0 and out.strip():
            try:
                parsed = json.loads(out)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, list):
                table: dict[str, Any] = {}
                for item in parsed:
                    if not isinstance(item, dict):
                        continue
                    name = item.get("value") or item.get("name")
                    if not name:
                        continue
                    entry: dict[str, Any] = {"type": str(item.get("type", "")).lower()}
                    data = item.get("data")
                    if isinstance(data, dict):
                        for bound in ("min", "max"):
                            if bound in data:
                                entry[bound] = data[bound]
                    table[canonical_option(str(name))] = entry
                if table:
                    return table, "hyprctl"
    return {canonical_option(k): v for k, v in _snapshot().items()}, "snapshot"


def canonical_option(name: str) -> str:
    """Normalise an option name the way Hyprland itself does.

    `CConfigManager::luaConfigValueName` maps `:` to `.` and `-` to `_`,
    so the hyprlang name `input:touchpad:tap-to-click` and the Lua key
    `input.touchpad.tap_to_click` are the same option. `hyprctl
    descriptions` reports the raw hyprlang form, so comparing against it
    without this collapses into false "unknown option" reports — which is
    exactly what once aborted an install over a config that was correct.
    """
    return name.replace(":", ".").replace("-", "_")


def validate_options(config: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Check a nested config table against Hyprland's own option list.

    Returns `(errors, warnings)`.

    A value outside a documented range is an error: the range came from
    the same table as the option, so it is provably wrong.

    An option the table does not list is only a **warning**. Our table is
    either a snapshot of one release or whatever the running compositor
    reports, and neither is a complete account of every version someone
    might run. Treating that gap as fatal means a newer or older Hyprland
    stops the desktop from being generated at all — which is a far worse
    failure than emitting an option the compositor will simply complain
    about in `hyprctl configerrors`.

    An empty option table reports nothing rather than inventing failures.
    """
    table, _ = options()
    if not table:
        return [], []

    problems: list[str] = []
    unknown: list[str] = []

    def walk(node: dict[str, Any], prefix: str) -> None:
        for key, value in node.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(value, dict):
                walk(value, path)
                continue
            option_key = canonical_option(path)
            meta = table.get(option_key)
            if meta is None:
                unknown.append(option_key)
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            low, high = meta.get("min"), meta.get("max")
            if isinstance(low, (int, float)) and value < low:
                problems.append(f"{option_key} = {value} is below the minimum {low}")
            if isinstance(high, (int, float)) and value > high:
                problems.append(f"{option_key} = {value} is above the maximum {high}")

    walk(config, "")
    return problems, unknown
