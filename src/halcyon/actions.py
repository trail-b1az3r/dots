"""The desktop action API.

This is the only surface through which the AI assistant is allowed to
touch the machine. The rule it enforces is simple and absolute: the model
chooses an **action id** and a set of **named parameters**, and nothing
else. It never supplies a command line, a path to an interpreter, or a
shell fragment. Every parameter is checked against a declared type and
range before a handler sees it, and every handler builds an argv list —
no string is ever handed to a shell.

Actions that cannot be undone (reboot, shutdown, log out) are marked
destructive and refuse to run without explicit confirmation, so a
misheard sentence cannot end a session with unsaved work in it.
"""

from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Callable

from . import apps, desktop, hyprland, paths, power, settings as settings_module

Handler = Callable[[dict[str, Any], dict[str, Any]], tuple[bool, str]]


class ActionError(ValueError):
    """A request that is not allowed, or not well formed."""


@dataclass
class Param:
    name: str
    type: str = "string"
    required: bool = True
    description: str = ""
    choices: list[str] | None = None
    minimum: float | None = None
    maximum: float | None = None
    default: Any = None
    pattern: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class Action:
    id: str
    title: str
    category: str
    description: str
    handler: Handler
    params: list[Param] = field(default_factory=list)
    destructive: bool = False
    #: Gated on a setting the user controls, e.g. `privacy.allowWebAccess`.
    requires_setting: str | None = None

    def schema(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "description": self.description,
            "destructive": self.destructive,
            "params": [p.as_dict() for p in self.params],
        }


REGISTRY: dict[str, Action] = {}


def register(action: Action) -> Action:
    REGISTRY[action.id] = action
    return action


# ── Validation ─────────────────────────────────────────────────────────

_SAFE_NAME = re.compile(r"^[\w .:+@#/-]{1,128}$")


def _coerce(param: Param, value: Any) -> Any:
    if param.type == "bool":
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        if text in ("true", "yes", "on", "1"):
            return True
        if text in ("false", "no", "off", "0"):
            return False
        raise ActionError(f"{param.name} expects true or false, got {value!r}")

    if param.type in ("int", "float"):
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ActionError(f"{param.name} expects a number, got {value!r}") from None
        if param.minimum is not None and number < param.minimum:
            raise ActionError(f"{param.name} must be at least {param.minimum}")
        if param.maximum is not None and number > param.maximum:
            raise ActionError(f"{param.name} must be at most {param.maximum}")
        return int(number) if param.type == "int" else number

    if param.type == "enum":
        text = str(value).strip().lower()
        allowed = [str(c).lower() for c in (param.choices or [])]
        if text not in allowed:
            raise ActionError(
                f"{param.name} must be one of {', '.join(param.choices or [])}, got {value!r}"
            )
        return text

    if param.type == "path":
        expanded = os.path.abspath(os.path.expanduser(str(value)))
        home = os.path.abspath(os.path.expanduser("~"))
        # Confine the assistant to the user's own files. It is not a
        # privilege boundary on its own, but it stops a hallucinated path
        # from opening something under /etc or /proc.
        allowed_roots = [home, "/tmp", "/media", "/run/media", "/mnt"]
        if not any(
            expanded == root or expanded.startswith(root + os.sep)
            for root in allowed_roots
        ):
            raise ActionError(
                f"{param.name} must be inside your home directory or a mounted volume"
            )
        return expanded

    text = str(value)
    if param.pattern and not re.match(param.pattern, text):
        raise ActionError(f"{param.name} is not in the expected format")
    if param.type == "name" and not _SAFE_NAME.match(text):
        raise ActionError(f"{param.name} contains characters that are not allowed")
    if len(text) > 4096:
        raise ActionError(f"{param.name} is too long")
    return text


def validate(action: Action, params: dict[str, Any]) -> dict[str, Any]:
    """Check and coerce parameters; reject anything not declared."""
    declared = {p.name: p for p in action.params}
    unknown = sorted(set(params) - set(declared))
    if unknown:
        raise ActionError(
            f"{action.id} does not take {', '.join(unknown)}. "
            f"Allowed: {', '.join(declared) or 'no parameters'}"
        )

    resolved: dict[str, Any] = {}
    for name, param in declared.items():
        if name in params and params[name] is not None:
            resolved[name] = _coerce(param, params[name])
        elif param.default is not None:
            resolved[name] = param.default
        elif param.required:
            raise ActionError(f"{action.id} requires {name} ({param.description})")
    return resolved


@dataclass
class Invocation:
    ok: bool
    message: str
    action: str
    params: dict[str, Any] = field(default_factory=dict)
    needs_confirmation: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def invoke(
    action_id: str,
    params: dict[str, Any] | None = None,
    *,
    confirmed: bool = False,
    settings: dict[str, Any] | None = None,
) -> Invocation:
    """Run an action after validating it. Never raises for bad input."""
    settings = settings if settings is not None else settings_module.load()
    action = REGISTRY.get(action_id)
    if action is None:
        return Invocation(
            False,
            f"There is no action called {action_id!r}.",
            action_id,
        )

    if action.requires_setting:
        node: Any = settings
        for part in action.requires_setting.split("."):
            node = node.get(part, {}) if isinstance(node, dict) else False
        if not node:
            return Invocation(
                False,
                f"{action.title} is switched off in Settings "
                f"({action.requires_setting}).",
                action_id,
            )

    try:
        resolved = validate(action, params or {})
    except ActionError as exc:
        return Invocation(False, str(exc), action_id, params or {})

    if action.destructive and not confirmed:
        confirm_required = (
            settings.get("assistant", {})
            .get("privacy", {})
            .get("confirmDestructiveActions", True)
        )
        if confirm_required:
            return Invocation(
                False,
                f"{action.title} needs confirmation before it runs.",
                action_id,
                resolved,
                needs_confirmation=True,
            )

    try:
        ok, message = action.handler(resolved, settings)
    except Exception as exc:  # noqa: BLE001 — a handler must never take the caller down
        return Invocation(False, f"{action.title} failed: {exc}", action_id, resolved)
    return Invocation(ok, message, action_id, resolved)


def catalog() -> list[dict[str, Any]]:
    """Machine-readable descriptions, for the assistant's tool list."""
    return [action.schema() for action in REGISTRY.values()]


# ── Handlers ───────────────────────────────────────────────────────────


def _open_application(params: dict[str, Any], settings: dict[str, Any]):
    name = str(params["name"])
    application = apps.find(name)
    if application is None:
        return False, f"I could not find an application called {name!r}."
    if application.terminal:
        return desktop.open_terminal(settings, application.exec_argv)
    ok, message = desktop._spawn(application.exec_argv, cwd=application.path or None)
    return ok, (f"Opening {application.name}" if ok else message)


def _close_application(params: dict[str, Any], settings: dict[str, Any]):
    name = str(params["name"]).lower()
    if not hyprland.available():
        return False, "hyprctl is not available, so I cannot close windows."

    import json as _json
    import subprocess

    try:
        out = subprocess.run(
            ["hyprctl", "-j", "clients"], capture_output=True, text=True, timeout=6, check=False
        ).stdout
        clients = _json.loads(out)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return False, "I could not read the window list."

    matches = [
        client
        for client in clients
        if name in str(client.get("class", "")).lower()
        or name in str(client.get("title", "")).lower()
    ]
    if not matches:
        return False, f"Nothing matching {name!r} is open."
    for client in matches:
        address = client.get("address")
        if address:
            hyprland.dispatch(f'hl.dsp.window.close({{ window = "address:{address}" }})')
    return True, f"Closed {len(matches)} window(s) matching {name!r}."


def _switch_workspace(params: dict[str, Any], _settings: dict[str, Any]):
    index = int(params["index"])
    if not hyprland.dispatch(f"hl.dsp.focus({{ workspace = {index} }})"):
        return False, "Hyprland did not accept the workspace change."
    return True, f"Switched to workspace {index}."


def _move_window(params: dict[str, Any], _settings: dict[str, Any]):
    index = int(params["workspace"])
    if not hyprland.dispatch(
        f"hl.dsp.window.move({{ workspace = {index}, follow = true }})"
    ):
        return False, "Hyprland did not accept the window move."
    return True, f"Moved the window to workspace {index}."


def _set_power_profile(params: dict[str, Any], settings: dict[str, Any]):
    profile = str(params["profile"])
    backend = power.detect_backend(settings.get("power", {}).get("backend", "auto"))
    ok, message = power.set_profile(profile, backend)
    settings_module.set_value("power.profile", profile)
    from . import pipeline

    pipeline.apply(reload=True, outputs=("theme", "hypr-theme"))
    return ok or backend == "none", message


def _set_wallpaper(params: dict[str, Any], _settings: dict[str, Any]):
    from . import wallpaper

    return wallpaper.set_wallpaper(str(params["path"]))


def _next_wallpaper(_params: dict[str, Any], _settings: dict[str, Any]):
    from . import wallpaper

    return wallpaper.next_wallpaper()


def _set_mode(params: dict[str, Any], _settings: dict[str, Any]):
    from . import pipeline

    mode = str(params["mode"])
    settings_module.set_value("appearance.mode", mode)
    result = pipeline.apply()
    return True, f"Switched to {result.mode} mode."


def _open_settings(params: dict[str, Any], _settings: dict[str, Any]):
    section = str(params.get("section", "") or "")
    from . import shell

    return shell.call("settings", "open", [section] if section else [])


def _search_files(params: dict[str, Any], settings: dict[str, Any]):
    from .search import providers

    query = str(params["query"])
    results = providers.files_provider(query, settings, limit=10)
    if not results:
        return False, f"Nothing matched {query!r}."
    listing = "\n".join(f"- {r.title} ({r.subtitle})" for r in results)
    return True, f"Found {len(results)} match(es):\n{listing}"


def _web_search(params: dict[str, Any], settings: dict[str, Any]):
    import urllib.parse

    query = str(params["query"])
    template = str(
        settings.get("search", {}).get("webSearchUrl", "https://duckduckgo.com/?q={query}")
    )
    url = template.replace("{query}", urllib.parse.quote_plus(query))
    return desktop.open_path(url)


def _dnd(params: dict[str, Any], _settings: dict[str, Any]):
    state = str(params.get("state", "toggle"))
    current = bool(settings_module.get("notifications.doNotDisturb"))
    value = (not current) if state == "toggle" else state == "on"
    settings_module.set_value("notifications.doNotDisturb", value)
    from . import shell

    shell.call("notifications", "setDoNotDisturb", ["true" if value else "false"])
    return True, f"Do Not Disturb {'on' if value else 'off'}."


register(Action(
    id="app.open", title="Open an application", category="apps",
    description="Launch an installed application by name.",
    params=[Param("name", "name", description="the application's name")],
    handler=_open_application,
))
register(Action(
    id="app.close", title="Close an application", category="apps",
    description="Close every window whose class or title matches a name.",
    params=[Param("name", "name", description="the application's name")],
    handler=_close_application,
))
register(Action(
    id="terminal.open", title="Open a terminal", category="apps",
    description="Open the configured terminal emulator.",
    handler=lambda _p, s: desktop.open_terminal(s),
))
register(Action(
    id="file.open", title="Open a file or folder", category="apps",
    description="Open a path with its default application.",
    params=[Param("path", "path", description="the file or folder to open")],
    handler=lambda p, _s: desktop.open_path(str(p["path"])),
))

register(Action(
    id="volume.set", title="Set the volume", category="audio",
    description="Set the output volume to a percentage.",
    params=[Param("percent", "int", minimum=0, maximum=150, description="0 to 150")],
    handler=lambda p, _s: desktop.set_volume(int(p["percent"])),
))
register(Action(
    id="volume.adjust", title="Change the volume", category="audio",
    description="Raise or lower the output volume by a number of percentage points.",
    params=[Param("delta", "int", minimum=-100, maximum=100, description="-100 to 100")],
    handler=lambda p, _s: desktop.adjust_volume(int(p["delta"])),
))
register(Action(
    id="volume.mute", title="Mute or unmute output", category="audio",
    description="Mute, unmute, or toggle the speakers.",
    params=[Param("state", "enum", choices=["on", "off", "toggle"], default="toggle", required=False)],
    handler=lambda p, _s: desktop.mute_output(str(p.get("state", "toggle"))),
))
register(Action(
    id="mic.mute", title="Mute or unmute the microphone", category="audio",
    description="Mute, unmute, or toggle the microphone.",
    params=[Param("state", "enum", choices=["on", "off", "toggle"], default="toggle", required=False)],
    handler=lambda p, _s: desktop.mute_input(str(p.get("state", "toggle"))),
))
register(Action(
    id="media.control", title="Control playback", category="audio",
    description="Play, pause, or skip the current track.",
    params=[Param("command", "enum", choices=["play-pause", "play", "pause", "next", "previous", "stop"])],
    handler=lambda p, _s: desktop.media(str(p["command"])),
))

register(Action(
    id="brightness.set", title="Set the screen brightness", category="display",
    description="Set the display backlight to a percentage.",
    params=[Param("percent", "int", minimum=1, maximum=100)],
    handler=lambda p, _s: desktop.set_backlight(int(p["percent"])),
))
register(Action(
    id="brightness.adjust", title="Change the screen brightness", category="display",
    description="Raise or lower the display backlight.",
    params=[Param("delta", "int", minimum=-100, maximum=100)],
    handler=lambda p, _s: desktop.adjust_backlight(int(p["delta"])),
))
register(Action(
    id="keyboard.brightness", title="Set the keyboard backlight", category="display",
    description="Set the keyboard backlight to a percentage.",
    params=[Param("percent", "int", minimum=0, maximum=100)],
    handler=lambda p, _s: desktop.keyboard_backlight(int(p["percent"])),
))

register(Action(
    id="wifi.set", title="Turn Wi-Fi on or off", category="network",
    description="Enable, disable, or toggle the Wi-Fi radio.",
    params=[Param("state", "enum", choices=["on", "off", "toggle"], default="toggle", required=False)],
    handler=lambda p, _s: desktop.set_wifi(str(p.get("state", "toggle"))),
))
register(Action(
    id="bluetooth.set", title="Turn Bluetooth on or off", category="network",
    description="Enable, disable, or toggle Bluetooth.",
    params=[Param("state", "enum", choices=["on", "off", "toggle"], default="toggle", required=False)],
    handler=lambda p, _s: desktop.set_bluetooth(str(p.get("state", "toggle"))),
))
register(Action(
    id="airplane.set", title="Airplane mode", category="network",
    description="Turn every radio off, or back on.",
    params=[Param("state", "enum", choices=["on", "off", "toggle"], default="toggle", required=False)],
    handler=lambda p, _s: desktop.set_airplane_mode(str(p.get("state", "toggle"))),
))
register(Action(
    id="web.search", title="Search the web", category="network",
    description="Open a web search in the default browser.",
    params=[Param("query", "string", description="what to search for")],
    handler=_web_search,
    requires_setting="assistant.privacy.allowWebAccess",
))

register(Action(
    id="workspace.switch", title="Switch workspace", category="windows",
    description="Move to a workspace by number.",
    params=[Param("index", "int", minimum=1, maximum=20)],
    handler=_switch_workspace,
))
register(Action(
    id="window.move", title="Move the window to a workspace", category="windows",
    description="Send the focused window to a workspace and follow it.",
    params=[Param("workspace", "int", minimum=1, maximum=20)],
    handler=_move_window,
))
register(Action(
    id="window.close", title="Close the focused window", category="windows",
    description="Ask the focused window to close.",
    handler=lambda _p, _s: (
        hyprland.dispatch("hl.dsp.window.close()"),
        "Closed the focused window.",
    ),
))
register(Action(
    id="window.fullscreen", title="Toggle fullscreen", category="windows",
    description="Toggle fullscreen on the focused window.",
    handler=lambda _p, _s: (
        hyprland.dispatch('hl.dsp.window.fullscreen({ mode = "fullscreen" })'),
        "Toggled fullscreen.",
    ),
))

register(Action(
    id="wallpaper.set", title="Change the wallpaper", category="appearance",
    description="Set the desktop wallpaper to an image file.",
    params=[Param("path", "path", description="an image file")],
    handler=_set_wallpaper,
))
register(Action(
    id="wallpaper.next", title="Next wallpaper", category="appearance",
    description="Move to the next wallpaper in the rotation folder.",
    handler=_next_wallpaper,
))
register(Action(
    id="theme.mode", title="Switch light or dark mode", category="appearance",
    description="Switch the desktop between light and dark.",
    params=[Param("mode", "enum", choices=["light", "dark", "auto"])],
    handler=_set_mode,
))
register(Action(
    id="settings.open", title="Open Settings", category="appearance",
    description="Open the Settings app, optionally at a section.",
    params=[Param("section", "name", required=False, default="", description="a section name")],
    handler=_open_settings,
))
register(Action(
    id="notifications.dnd", title="Do Not Disturb", category="appearance",
    description="Turn Do Not Disturb on, off, or toggle it.",
    params=[Param("state", "enum", choices=["on", "off", "toggle"], default="toggle", required=False)],
    handler=_dnd,
))

register(Action(
    id="power.profile", title="Change the power profile", category="power",
    description="Switch between performance, balanced and battery saver.",
    params=[Param("profile", "enum", choices=list(power.PROFILES))],
    handler=_set_power_profile,
))
register(Action(
    id="session.lock", title="Lock the screen", category="power",
    description="Lock the session immediately.",
    handler=lambda _p, _s: desktop.lock(),
))
register(Action(
    id="session.suspend", title="Suspend", category="power",
    description="Put the machine to sleep.",
    handler=lambda _p, _s: desktop.suspend(),
    destructive=True,
))
register(Action(
    id="session.reboot", title="Restart", category="power",
    description="Restart the machine.",
    handler=lambda _p, _s: desktop.reboot(),
    destructive=True,
))
register(Action(
    id="session.shutdown", title="Shut down", category="power",
    description="Power the machine off.",
    handler=lambda _p, _s: desktop.shutdown(),
    destructive=True,
))
register(Action(
    id="session.logout", title="Log out", category="power",
    description="End the desktop session.",
    handler=lambda _p, _s: desktop.logout(),
    destructive=True,
))

register(Action(
    id="screenshot.take", title="Take a screenshot", category="capture",
    description="Capture the screen, a region, or the focused window.",
    params=[Param("mode", "enum", choices=["screen", "region", "window"], default="screen", required=False)],
    handler=lambda p, s: desktop.screenshot(str(p.get("mode", "screen")), s),
))
register(Action(
    id="file.search", title="Search for files", category="apps",
    description="Find files and folders by name.",
    params=[Param("query", "string", description="part of a file name")],
    handler=_search_files,
))
