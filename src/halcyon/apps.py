"""The installed-application index.

Reads `.desktop` files the way the freedesktop spec says to: XDG data
dirs in precedence order, later entries shadowed by earlier ones, NoDisplay
and Hidden respected, `%f`/`%u` field codes stripped from Exec.

The index is cached on disk with an mtime fingerprint because Spotlight
has to feel instant, and walking a few hundred desktop files on every
keystroke does not.
"""

from __future__ import annotations

import json
import os
import shlex
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

from . import paths

_FIELD_CODES = {"%f", "%F", "%u", "%U", "%d", "%D", "%n", "%N", "%i", "%c", "%k", "%v", "%m"}


@dataclass
class Application:
    id: str
    name: str
    exec_argv: list[str] = field(default_factory=list)
    icon: str = ""
    comment: str = ""
    generic_name: str = ""
    categories: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    terminal: bool = False
    path: str = ""
    startup_wm_class: str = ""
    desktop_file: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def search_text(self) -> str:
        return " ".join(
            [self.name, self.generic_name, self.comment, " ".join(self.keywords)]
        ).lower()


def data_dirs() -> list[str]:
    dirs = [str(paths.XDG_DATA_HOME)]
    extra = os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share"
    dirs.extend(part for part in extra.split(":") if part)
    # Flatpak installs land outside XDG_DATA_DIRS on several distributions.
    dirs.extend(
        [
            "/var/lib/flatpak/exports/share",
            os.path.expanduser("~/.local/share/flatpak/exports/share"),
        ]
    )
    seen: set[str] = set()
    ordered: list[str] = []
    for directory in dirs:
        resolved = os.path.normpath(directory)
        if resolved in seen:
            continue
        seen.add(resolved)
        ordered.append(resolved)
    return ordered


def _application_dirs() -> list[str]:
    return [os.path.join(directory, "applications") for directory in data_dirs()]


def _parse_desktop(path: str) -> Application | None:
    """Parse the `[Desktop Entry]` group of a .desktop file.

    Hand-rolled rather than configparser: desktop files contain keys with
    locale suffixes (`Name[de]`) and values with `%` and `=` in them, and
    configparser's interpolation trips over both.
    """
    entry: dict[str, str] = {}
    in_entry = False
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("["):
                    in_entry = line == "[Desktop Entry]"
                    continue
                if not in_entry or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                # Ignore localised variants; we index the C locale.
                if "[" in key:
                    continue
                entry[key] = value.strip()
    except OSError:
        return None

    if entry.get("Type", "Application") != "Application":
        return None
    if entry.get("NoDisplay", "").lower() == "true":
        return None
    if entry.get("Hidden", "").lower() == "true":
        return None
    name = entry.get("Name")
    exec_line = entry.get("Exec")
    if not name or not exec_line:
        return None

    try:
        argv = [token for token in shlex.split(exec_line) if token not in _FIELD_CODES]
    except ValueError:
        argv = [token for token in exec_line.split() if token not in _FIELD_CODES]
    # A field code glued to another token (`--file=%f`) still has to go.
    argv = [token for token in argv if not any(code in token for code in _FIELD_CODES)]
    if not argv:
        return None

    return Application(
        id=os.path.basename(path)[: -len(".desktop")],
        name=name,
        exec_argv=argv,
        icon=entry.get("Icon", ""),
        comment=entry.get("Comment", ""),
        generic_name=entry.get("GenericName", ""),
        categories=[c for c in entry.get("Categories", "").split(";") if c],
        keywords=[k for k in entry.get("Keywords", "").split(";") if k],
        terminal=entry.get("Terminal", "").lower() == "true",
        path=entry.get("Path", ""),
        startup_wm_class=entry.get("StartupWMClass", ""),
        desktop_file=path,
    )


def _fingerprint(directories: Iterable[str]) -> str:
    """Cheap change detector: directory mtimes, not file contents."""
    parts: list[str] = []
    for directory in directories:
        try:
            parts.append(f"{directory}:{int(os.stat(directory).st_mtime)}")
        except OSError:
            continue
    return "|".join(parts)


def scan() -> list[Application]:
    """Walk the application directories, honouring shadowing."""
    found: dict[str, Application] = {}
    for directory in _application_dirs():
        if not os.path.isdir(directory):
            continue
        for root, _dirs, files in os.walk(directory):
            for filename in files:
                if not filename.endswith(".desktop"):
                    continue
                relative = os.path.relpath(os.path.join(root, filename), directory)
                key = relative.replace(os.sep, "-")[: -len(".desktop")]
                if key in found:
                    # Earlier directories win, per the spec.
                    continue
                application = _parse_desktop(os.path.join(root, filename))
                if application is not None:
                    application.id = key
                    found[key] = application
    return sorted(found.values(), key=lambda app: app.name.lower())


def _cache_file() -> str:
    return str(paths.CACHE_DIR / "applications.json")


def load(*, refresh: bool = False) -> list[Application]:
    """The application list, from cache when it is still valid."""
    directories = [d for d in _application_dirs() if os.path.isdir(d)]
    fingerprint = _fingerprint(directories)
    cache_path = _cache_file()

    if not refresh:
        try:
            with open(cache_path, "r", encoding="utf-8") as handle:
                cached = json.load(handle)
            if cached.get("fingerprint") == fingerprint:
                return [Application(**item) for item in cached["applications"]]
        except (OSError, ValueError, TypeError, KeyError):
            pass

    applications = scan()
    try:
        paths.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "fingerprint": fingerprint,
                    "scanned": int(time.time()),
                    "applications": [app.as_dict() for app in applications],
                },
                handle,
            )
    except OSError:
        pass
    return applications


def find(query: str) -> Application | None:
    """Best match for a name the user (or the assistant) typed.

    Exact id, then exact name, then prefix, then substring — in that
    order, so "files" does not launch "File Roller" when a "Files" exists.
    """
    needle = query.strip().lower()
    if not needle:
        return None
    applications = load()

    for app in applications:
        if app.id.lower() == needle:
            return app
    for app in applications:
        if app.name.lower() == needle:
            return app
    for app in applications:
        if app.name.lower().startswith(needle):
            return app
    for app in applications:
        if needle in app.search_text:
            return app
    # Last resort: an executable of that name, which covers CLI tools that
    # ship no desktop file.
    import shutil

    binary = shutil.which(needle)
    if binary:
        return Application(id=needle, name=needle, exec_argv=[binary], terminal=True)
    return None
