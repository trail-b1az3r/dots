"""HyperNix integration.

HyperNix is a separate project — a model training and quantisation
toolkit with its own CLI (`hypernix`, aliased `hnx`). Halcyon treats it
as an optional integration, not a dependency: everything here probes for
the binary first, reports honestly when it is absent, and can be switched
off entirely from Settings without affecting anything else.

The only interface used is the documented CLI, and only the read-only
parts of it: `--version`, `devices --json`, and `doctor`. Halcyon never
starts or stops a training run on its own.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Any

from . import desktop, settings as settings_module


def command(settings: dict[str, Any] | None = None) -> str | None:
    """The HyperNix entry point, honouring the configured override."""
    settings = settings or settings_module.load()
    configured = str(settings.get("hypernix", {}).get("command", "hypernix")).strip()
    for candidate in (configured, "hypernix", "hnx"):
        if candidate and shutil.which(candidate):
            return shutil.which(candidate)
    return None


def enabled(settings: dict[str, Any] | None = None) -> bool:
    settings = settings or settings_module.load()
    return bool(settings.get("hypernix", {}).get("enabled", True))


def available(settings: dict[str, Any] | None = None) -> bool:
    return enabled(settings) and command(settings) is not None


def _run(argv: list[str], timeout: float = 15.0) -> tuple[int, str]:
    try:
        done = subprocess.run(
            argv, capture_output=True, text=True, timeout=timeout, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""
    return done.returncode, done.stdout.strip()


def version(settings: dict[str, Any] | None = None) -> str | None:
    binary = command(settings)
    if binary is None:
        return None
    code, out = _run([binary, "--version"], timeout=20)
    if code != 0 or not out:
        return None
    # The CLI prints "hypernix <version>", sometimes with a typewriter
    # animation, so take the last whitespace-separated token of line one.
    first = out.splitlines()[0].strip()
    return first.split()[-1] if first else None


def devices(settings: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Accelerators HyperNix can use, straight from `devices --json`."""
    binary = command(settings)
    if binary is None:
        return None
    code, out = _run([binary, "devices", "--json"], timeout=30)
    if code != 0 or not out:
        return None
    try:
        parsed = json.loads(out)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def status(settings: dict[str, Any] | None = None) -> dict[str, Any]:
    """Everything the widget, Spotlight and diagnostics need, in one call."""
    settings = settings or settings_module.load()

    if not enabled(settings):
        return {"enabled": False, "installed": False, "summary": "HyperNix integration is off"}

    binary = command(settings)
    if binary is None:
        return {
            "enabled": True,
            "installed": False,
            "summary": "HyperNix is not installed",
            "hint": "pip install hypernix",
        }

    info: dict[str, Any] = {
        "enabled": True,
        "installed": True,
        "binary": binary,
        "version": version(settings),
    }

    device_info = devices(settings)
    if device_info:
        found = device_info.get("devices") or []
        info["deviceCount"] = len(found)
        info["autoDevice"] = device_info.get("auto")
        names = [
            str(item.get("name") or item.get("kind") or "device")
            for item in found
            if isinstance(item, dict)
        ]
        info["devices"] = names
        info["summary"] = (
            f"{device_info.get('auto', 'auto')} · {len(found)} device(s)"
            if found
            else "no accelerators detected"
        )
    else:
        info["summary"] = f"HyperNix {info.get('version') or ''}".strip()

    return info


def waybar_status(settings: dict[str, Any] | None = None) -> dict[str, Any]:
    settings = settings or settings_module.load()
    info = status(settings)

    if not info["enabled"]:
        return {"text": "", "tooltip": "", "class": "disabled"}
    if not info["installed"]:
        return {
            "text": "󰆧",
            "tooltip": "HyperNix is not installed\nInstall it with: pip install hypernix",
            "class": "missing",
        }

    tooltip = [f"HyperNix {info.get('version') or ''}".strip()]
    if info.get("devices"):
        tooltip.append("Accelerators: " + ", ".join(info["devices"]))
    if info.get("autoDevice"):
        tooltip.append(f"Auto-selected: {info['autoDevice']}")
    tooltip.append("Click to open · right-click for settings")

    return {
        "text": "󰆧",
        "tooltip": "\n".join(tooltip),
        "class": "ready",
        "alt": "ready",
    }


def launch(settings: dict[str, Any] | None = None) -> tuple[bool, str]:
    """Open HyperNix the way it is meant to be used: in a terminal."""
    settings = settings or settings_module.load()
    binary = command(settings)
    if binary is None:
        return False, "HyperNix is not installed (pip install hypernix)."

    # `hyped` is HyperNix's own interactive TUI; prefer it when present,
    # and fall back to the CLI's help so the window is never empty.
    for candidate in ("hyped-pro", "hyped"):
        found = shutil.which(candidate)
        if found:
            return desktop.open_terminal(settings, [found])
    return desktop.open_terminal(settings, [binary, "--help"])


def spotlight_entries(settings: dict[str, Any] | None = None) -> list[dict[str, str]]:
    """The HyperNix actions Spotlight should offer.

    Only read-only or interactive-launch entries: Spotlight will not start
    a quantisation run behind the user's back.
    """
    settings = settings or settings_module.load()
    if not available(settings):
        return []
    if not settings.get("hypernix", {}).get("showInSpotlight", True):
        return []

    binary = command(settings) or "hypernix"
    return [
        {
            "id": "hypernix.open",
            "title": "HyperNix",
            "subtitle": "Open the HyperNix agent TUI",
            "command": "launch",
        },
        {
            "id": "hypernix.devices",
            "title": "HyperNix: Accelerators",
            "subtitle": "Show which GPUs HyperNix can use",
            "command": f"{binary} devices",
        },
        {
            "id": "hypernix.doctor",
            "title": "HyperNix: Doctor",
            "subtitle": "Diagnose the HyperNix environment",
            "command": f"{binary} doctor",
        },
        {
            "id": "hypernix.chat",
            "title": "HyperNix: Chat",
            "subtitle": "Interactive chat against a local model",
            "command": f"{binary} chat",
        },
        {
            "id": "hypernix.settings",
            "title": "HyperNix settings",
            "subtitle": "Halcyon's HyperNix integration options",
            "command": "settings",
        },
    ]
