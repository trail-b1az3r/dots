"""Spotlight's result providers.

Each provider is a plain function `(query, settings, limit) -> [Result]`.
Adding a source of results means writing one function and listing it in
`REGISTRY` — there is no plugin framework to learn, and no provider can
slow the others down because the orchestrator gives each one a time
budget.

Providers never block on the network unless the user has allowed it.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
import urllib.parse
from dataclasses import asdict, dataclass, field
from typing import Any, Callable

from .. import actions as actions_module
from .. import apps as apps_module
from .. import hypernix as hypernix_module
from .. import paths
from . import calc, match


@dataclass
class Result:
    """One row in the Spotlight list."""

    id: str
    provider: str
    title: str
    subtitle: str = ""
    icon: str = ""
    score: float = 0.0
    #: What to do when it is chosen, e.g.
    #: {"type": "action", "action": "app.open", "params": {...}}
    activate: dict[str, Any] = field(default_factory=dict)
    #: Optional larger text shown in the preview pane.
    detail: str = ""
    category: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


Provider = Callable[[str, dict[str, Any], int], list[Result]]


# ── Applications ───────────────────────────────────────────────────────


def applications_provider(query: str, settings: dict[str, Any], limit: int) -> list[Result]:
    if not query:
        return []
    results: list[Result] = []
    for app in apps_module.load():
        value = match.score(
            query, app.name, app.generic_name, app.id, " ".join(app.keywords), app.comment,
            weights=(1.0, 0.75, 0.7, 0.6, 0.4),
        )
        if value is None:
            continue
        results.append(
            Result(
                id=f"app:{app.id}",
                provider="applications",
                title=app.name,
                subtitle=app.generic_name or app.comment or "Application",
                icon=app.icon or "application-x-executable",
                score=value,
                category="Applications",
                activate={"type": "action", "action": "app.open", "params": {"name": app.id}},
            )
        )
    results.sort(key=lambda r: r.score, reverse=True)
    return results[:limit]


# ── Files ──────────────────────────────────────────────────────────────

_SKIP_DIRS = {
    ".git", ".svn", "node_modules", "__pycache__", ".venv", "venv",
    ".cache", ".local/share/Trash", "target", ".next", ".gradle", ".cargo",
}


#: Leading words people type before a target. Stripping them is what
#: makes "open downloads" find the folder instead of searching for the
#: literal phrase.
_OPEN_VERBS = re.compile(
    r"^(open|go\s+to|show|reveal|find|browse|launch|edit)\s+", re.IGNORECASE
)


def files_provider(query: str, settings: dict[str, Any], limit: int) -> list[Result]:
    """Walk the configured roots, breadth-first, on a time budget.

    A plain `os.walk` over a home directory can take seconds; Spotlight
    has milliseconds. The walk is bounded by depth, by result count and
    by wall-clock, and returns what it found when any of the three runs
    out — partial results now beat complete results later.
    """
    needle = query.strip()
    stripped = _OPEN_VERBS.sub("", needle).strip()
    directories_first = stripped != needle and bool(stripped)
    if directories_first:
        needle = stripped
    if len(needle) < 2:
        return []

    search = settings.get("search", {})
    roots = [
        os.path.expanduser(str(root))
        for root in search.get("fileRoots", ["~"])
    ]
    max_depth = int(search.get("fileDepth", 4))
    deadline = time.monotonic() + 0.35

    results: list[Result] = []
    seen: set[str] = set()
    queue: list[tuple[str, int]] = [(root, 0) for root in roots if os.path.isdir(root)]

    while queue and len(results) < limit * 4:
        if time.monotonic() > deadline:
            break
        directory, depth = queue.pop(0)
        try:
            entries = list(os.scandir(directory))
        except OSError:
            continue

        for entry in entries:
            name = entry.name
            if name.startswith("."):
                continue
            try:
                is_dir = entry.is_dir(follow_symlinks=False)
            except OSError:
                continue

            if is_dir:
                if name in _SKIP_DIRS:
                    continue
                if depth < max_depth:
                    queue.append((entry.path, depth + 1))

            value = match.score(needle, name)
            if value is None or entry.path in seen:
                continue
            seen.add(entry.path)
            results.append(
                Result(
                    id=f"file:{entry.path}",
                    provider="files",
                    title=name,
                    subtitle=_pretty_path(os.path.dirname(entry.path)),
                    icon="folder" if is_dir else "text-x-generic",
                    # Folders rank above files, and much further above
                    # when the query opened with a verb like "open".
                    score=value * ((1.6 if directories_first else 1.08) if is_dir else 1.0),
                    category="Folders" if is_dir else "Files",
                    activate={
                        "type": "action",
                        "action": "file.open",
                        "params": {"path": entry.path},
                    },
                )
            )

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:limit]


def _pretty_path(path: str) -> str:
    home = os.path.expanduser("~")
    return "~" + path[len(home):] if path.startswith(home) else path


# ── Commands on PATH ───────────────────────────────────────────────────


def commands_provider(query: str, settings: dict[str, Any], limit: int) -> list[Result]:
    needle = query.strip()
    if len(needle) < 2:
        return []

    prefix = ""
    if needle.startswith(">"):
        prefix = ">"
        needle = needle[1:].strip()
        if not needle:
            return []

    results: list[Result] = []
    seen: set[str] = set()
    deadline = time.monotonic() + 0.15

    for directory in os.environ.get("PATH", "").split(os.pathsep):
        if not directory or time.monotonic() > deadline:
            break
        try:
            entries = os.listdir(directory)
        except OSError:
            continue
        for name in entries:
            if name in seen:
                continue
            value = match.score(needle, name)
            # Without a `>` prefix, only exact-ish matches: nobody wants
            # every binary on PATH that shares three letters with a word.
            if value is None or (not prefix and value < 400):
                continue
            full = os.path.join(directory, name)
            if not os.access(full, os.X_OK) or os.path.isdir(full):
                continue
            seen.add(name)
            results.append(
                Result(
                    id=f"cmd:{name}",
                    provider="commands",
                    title=name,
                    subtitle=f"Run in a terminal · {_pretty_path(directory)}",
                    icon="utilities-terminal",
                    score=value * 0.8,
                    category="Commands",
                    activate={
                        "type": "action",
                        "action": "app.open",
                        "params": {"name": name},
                    },
                )
            )
            if len(results) >= limit * 2:
                break

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:limit]


# ── Calculator and conversion ──────────────────────────────────────────


def calculator_provider(query: str, settings: dict[str, Any], limit: int) -> list[Result]:
    value = calc.calculate(query)
    if value is None:
        return []
    text = calc.format_number(value)
    return [
        Result(
            id="calc:result",
            provider="calculator",
            title=text,
            subtitle=f"{query.strip()} =",
            icon="accessories-calculator",
            # Pinned above everything: when a query is arithmetic, the
            # answer is what was wanted.
            score=10_000.0,
            category="Calculator",
            detail=text,
            activate={"type": "copy", "text": text},
        )
    ]


def units_provider(query: str, settings: dict[str, Any], limit: int) -> list[Result]:
    allow_network = bool(
        settings.get("assistant", {}).get("privacy", {}).get("allowWebAccess", False)
    )
    converted = calc.convert(query, allow_network=allow_network)
    if converted is None:
        return []
    return [
        Result(
            id="units:result",
            provider="units",
            title=converted["text"],
            subtitle=converted.get("detail", ""),
            icon="accessories-calculator",
            score=9_800.0,
            category="Conversion",
            detail=converted["text"],
            activate={"type": "copy", "text": converted["text"]},
        )
    ]


# ── Open windows ───────────────────────────────────────────────────────


def windows_provider(query: str, settings: dict[str, Any], limit: int) -> list[Result]:
    if not query or shutil.which("hyprctl") is None:
        return []
    import json as _json

    try:
        out = subprocess.run(
            ["hyprctl", "-j", "clients"],
            capture_output=True, text=True, timeout=2, check=False,
        ).stdout
        clients = _json.loads(out)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return []

    results: list[Result] = []
    for client in clients:
        if not isinstance(client, dict) or client.get("mapped") is False:
            continue
        title = str(client.get("title", "")).strip()
        klass = str(client.get("class", "")).strip()
        if not title and not klass:
            continue
        value = match.score(query, title, klass, weights=(1.0, 0.8))
        if value is None:
            continue
        workspace = client.get("workspace", {}) or {}
        results.append(
            Result(
                id=f"win:{client.get('address')}",
                provider="windows",
                title=title or klass,
                subtitle=f"Open window · {klass} · workspace {workspace.get('name', '?')}",
                icon=klass.lower(),
                score=value * 1.05,
                category="Open Windows",
                activate={
                    "type": "dispatch",
                    "expression": f'hl.dsp.focus({{ window = "address:{client.get("address")}" }})',
                },
            )
        )
    results.sort(key=lambda r: r.score, reverse=True)
    return results[:limit]


# ── Actions, settings, power ───────────────────────────────────────────

_SETTINGS_SECTIONS = [
    ("appearance", "Appearance", "Mode, accent colour, fonts and icons"),
    ("glass", "Liquid Glass", "Opacity, blur, tint, corner radius and shadows"),
    ("wallpaper", "Wallpaper", "Image, rotation and derived colours"),
    ("animations", "Animations", "Motion presets, speed and reduced motion"),
    ("keybinds", "Keyboard Shortcuts", "Rebind anything on the desktop"),
    ("workspaces", "Workspaces", "Count, names, per-monitor behaviour"),
    ("displays", "Displays", "Resolution, scaling, refresh rate and VRR"),
    ("audio", "Audio", "Output, input and volume behaviour"),
    ("network", "Network", "Wi-Fi and wired connections"),
    ("bluetooth", "Bluetooth", "Devices and pairing"),
    ("notifications", "Notifications", "Do Not Disturb, timeouts and history"),
    ("battery", "Battery", "Idle timeouts and adaptive effects"),
    ("performance", "Performance", "Blur, shadow and animation quality"),
    ("assistant", "AI Assistant", "Provider, voice, wake word and privacy"),
    ("hypernix", "HyperNix", "Toolkit integration and widget"),
    ("applications", "Applications", "Default terminal, browser and file manager"),
    ("privacy", "Privacy", "Clipboard history, web access and screen context"),
    ("accessibility", "Accessibility", "Reduced motion, contrast and text size"),
    ("about", "About", "Versions, diagnostics and backups"),
]


def settings_provider(query: str, settings: dict[str, Any], limit: int) -> list[Result]:
    if not query:
        return []
    results: list[Result] = []
    for key, title, description in _SETTINGS_SECTIONS:
        value = match.score(query, title, key, description, weights=(1.0, 0.8, 0.45))
        if value is None:
            continue
        results.append(
            Result(
                id=f"settings:{key}",
                provider="settings",
                title=title,
                subtitle=description,
                icon="preferences-system",
                score=value * 0.95,
                category="Settings",
                activate={
                    "type": "action",
                    "action": "settings.open",
                    "params": {"section": key},
                },
            )
        )
    results.sort(key=lambda r: r.score, reverse=True)
    return results[:limit]


def actions_provider(query: str, settings: dict[str, Any], limit: int) -> list[Result]:
    if not query:
        return []
    results: list[Result] = []
    for action in actions_module.REGISTRY.values():
        required = [p for p in action.params if p.required]

        # An action whose only required parameter is a short enum can
        # still be offered — once per choice — because every option is
        # nameable. "dark" should reach light/dark mode directly.
        if len(required) == 1 and required[0].type == "enum" and required[0].choices:
            parameter = required[0]
            for choice in parameter.choices or []:
                value = match.score(
                    query,
                    f"{action.title} {choice}",
                    choice,
                    action.description,
                    weights=(1.0, 0.95, 0.35),
                )
                if value is None:
                    continue
                results.append(
                    Result(
                        id=f"action:{action.id}:{choice}",
                        provider="actions",
                        title=f"{action.title} → {choice}",
                        subtitle=action.description,
                        icon="system-run",
                        score=value * (0.8 if action.destructive else 0.9),
                        category="System Actions",
                        activate={
                            "type": "action",
                            "action": action.id,
                            "params": {parameter.name: choice},
                            "confirm": action.destructive,
                        },
                    )
                )
            continue

        # Anything else that needs a value is not a one-click result:
        # "Set the volume" with no number attached does nothing useful.
        if required:
            continue

        value = match.score(query, action.title, action.id, action.description, weights=(1.0, 0.7, 0.4))
        if value is None:
            continue
        results.append(
            Result(
                id=f"action:{action.id}",
                provider="actions",
                title=action.title,
                subtitle=action.description,
                icon="system-run",
                score=value * (0.8 if action.destructive else 0.92),
                category="System Actions",
                activate={
                    "type": "action",
                    "action": action.id,
                    "params": {},
                    "confirm": action.destructive,
                },
            )
        )
    results.sort(key=lambda r: r.score, reverse=True)
    return results[:limit]


def power_provider(query: str, settings: dict[str, Any], limit: int) -> list[Result]:
    from .. import power as power_module

    if not query:
        return []
    results: list[Result] = []
    for profile in power_module.PROFILES:
        label = profile.replace("-", " ").title()
        value = match.score(query, f"{label} power profile", profile, weights=(1.0, 0.8))
        if value is None:
            continue
        results.append(
            Result(
                id=f"power:{profile}",
                provider="power",
                title=f"{label} power profile",
                subtitle="Switch the system power profile",
                icon="battery",
                score=value * 0.9,
                category="Power",
                activate={
                    "type": "action",
                    "action": "power.profile",
                    "params": {"profile": profile},
                },
            )
        )
    results.sort(key=lambda r: r.score, reverse=True)
    return results[:limit]


# ── Clipboard and recent files ─────────────────────────────────────────


def clipboard_provider(query: str, settings: dict[str, Any], limit: int) -> list[Result]:
    if not settings.get("privacy", {}).get("clipboardHistory", True):
        return []
    if shutil.which("cliphist") is None:
        return []
    try:
        out = subprocess.run(
            ["cliphist", "list"], capture_output=True, text=True, timeout=2, check=False
        ).stdout
    except (OSError, subprocess.TimeoutExpired):
        return []

    results: list[Result] = []
    for line in out.splitlines():
        identifier, _, preview = line.partition("\t")
        if not preview:
            continue
        value = match.score(query, preview) if query else 100.0
        if value is None:
            continue
        results.append(
            Result(
                id=f"clip:{identifier}",
                provider="clipboard",
                title=preview[:120],
                subtitle="Clipboard history",
                icon="edit-paste",
                score=value * 0.85,
                category="Clipboard",
                activate={"type": "clipboard", "entry": identifier},
            )
        )
        if len(results) >= limit * 3:
            break

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:limit]


_RECENT_RE = re.compile(r'href="([^"]+)"')


def recent_provider(query: str, settings: dict[str, Any], limit: int) -> list[Result]:
    if not settings.get("privacy", {}).get("recentFiles", True):
        return []
    path = paths.XDG_DATA_HOME / "recently-used.xbel"
    try:
        body = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    results: list[Result] = []
    seen: set[str] = set()
    for href in reversed(_RECENT_RE.findall(body)):
        if not href.startswith("file://"):
            continue
        target = urllib.parse.unquote(href[len("file://"):])
        if target in seen or not os.path.exists(target):
            continue
        seen.add(target)
        name = os.path.basename(target)
        value = match.score(query, name) if query else 100.0
        if value is None:
            continue
        results.append(
            Result(
                id=f"recent:{target}",
                provider="recent",
                title=name,
                subtitle=f"Recent · {_pretty_path(os.path.dirname(target))}",
                icon="document-open-recent",
                score=value * 0.88,
                category="Recent",
                activate={"type": "action", "action": "file.open", "params": {"path": target}},
            )
        )
        if len(results) >= limit * 2:
            break

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:limit]


# ── Web, assistant, HyperNix ───────────────────────────────────────────


def web_provider(query: str, settings: dict[str, Any], limit: int) -> list[Result]:
    needle = query.strip()
    if len(needle) < 2:
        return []
    search = settings.get("search", {})
    name = str(search.get("webSearchName", "the web"))
    return [
        Result(
            id="web:search",
            provider="web",
            title=f"Search {name} for “{needle}”",
            subtitle="Opens in your browser",
            icon="web-browser",
            # Always last: a web search is the fallback when nothing local
            # matched, never the answer competing with a real one.
            score=1.0,
            category="Web",
            activate={"type": "action", "action": "web.search", "params": {"query": needle}},
        )
    ]


def assistant_provider(query: str, settings: dict[str, Any], limit: int) -> list[Result]:
    needle = query.strip()
    if len(needle) < 3 or not settings.get("assistant", {}).get("enabled", True):
        return []
    return [
        Result(
            id="assistant:ask",
            provider="assistant",
            title=f"Ask Halcyon: “{needle}”",
            subtitle="Send this to the assistant",
            icon="system-help",
            score=2.0,
            category="Assistant",
            activate={"type": "assistant", "prompt": needle},
        )
    ]


def hypernix_provider(query: str, settings: dict[str, Any], limit: int) -> list[Result]:
    if not query:
        return []
    results: list[Result] = []
    for entry in hypernix_module.spotlight_entries(settings):
        value = match.score(query, entry["title"], "hypernix", entry["subtitle"], weights=(1.0, 0.9, 0.4))
        if value is None:
            continue
        if entry["command"] == "launch":
            activate: dict[str, Any] = {"type": "hypernix", "command": "launch"}
        elif entry["command"] == "settings":
            activate = {
                "type": "action",
                "action": "settings.open",
                "params": {"section": "hypernix"},
            }
        else:
            activate = {"type": "hypernix", "command": entry["command"]}
        results.append(
            Result(
                id=entry["id"],
                provider="hypernix",
                title=entry["title"],
                subtitle=entry["subtitle"],
                icon="applications-science",
                score=value * 0.95,
                category="HyperNix",
                activate=activate,
            )
        )
    results.sort(key=lambda r: r.score, reverse=True)
    return results[:limit]


REGISTRY: dict[str, Provider] = {
    "calculator": calculator_provider,
    "units": units_provider,
    "applications": applications_provider,
    "windows": windows_provider,
    "settings": settings_provider,
    "actions": actions_provider,
    "power": power_provider,
    "hypernix": hypernix_provider,
    "files": files_provider,
    "recent": recent_provider,
    "commands": commands_provider,
    "clipboard": clipboard_provider,
    "assistant": assistant_provider,
    "web": web_provider,
}
