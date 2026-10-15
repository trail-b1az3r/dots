"""The revolver widget's pool: installed games, weighted, and how to launch them.

The desktop widget spins a drum of chambers, one per installed game, and
launches whichever chamber stops under the firing pin. This module
produces that pool. It only reads files that already exist on this
machine (Steam's library manifests and PrismLauncher's instance folders),
and it only ever launches through a fixed argument list. No shell is
involved, and no value from a file is ever run as a command.

The scanning approach follows hyprland-revolver (MIT License,
Copyright (c) 2026 minerofthesoal), which first worked out how to read
Steam's library without a Web API key. The code here is written for
Halcyon, and it omits that project's achievement parsing, which depends
on an undocumented binary format.
"""

from __future__ import annotations

import math
import random
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterator, Optional, Union

#: The sources the widget can draw from.
SOURCES = ("steam", "prismlauncher")

#: How a pool is weighted. `random` is uniform; `recent` favours what was
#: played lately; `recommended` favours recent games and ones left
#: untouched for a while, which is what "pick up where you left off, or
#: revisit something" means.
MODES = ("recent", "random", "recommended")

DAY = 86400.0

_STEAM_ID = re.compile(r"^\d{1,12}$")
_INSTANCE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._+()-]{0,127}$")


@dataclass(frozen=True)
class Chamber:
    """One game in the pool."""

    id: str
    name: str
    source: str
    weight: float
    last_played: Optional[float] = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Valve's KeyValues format (Steam's manifests and library list) ──────

Node = Union[str, dict[str, "Node"]]


def parse_vdf(text: str) -> dict[str, Node]:
    """Parse Valve KeyValues into nested dictionaries.

    The format is `"key" "value"` pairs, with `"key" { ... }` for nested
    sections. Anything that cannot be parsed stops the parse at that point
    and what came before is returned, so a damaged manifest costs one game
    rather than the whole library.
    """
    tokens = _tokenise(text)
    root: dict[str, Node] = {}
    stack: list[dict[str, Node]] = [root]
    pending: Optional[str] = None
    for token in tokens:
        if token == "{":
            if pending is None:
                break
            section: dict[str, Node] = {}
            stack[-1][pending] = section
            stack.append(section)
            pending = None
        elif token == "}":
            if len(stack) == 1:
                break
            stack.pop()
        elif pending is None:
            pending = token
        else:
            stack[-1][pending] = token
            pending = None
    return root


def _tokenise(text: str) -> Iterator[str]:
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch in " \t\r\n":
            i += 1
        elif ch == "/" and text.startswith("//", i):
            end = text.find("\n", i)
            i = n if end < 0 else end + 1
        elif ch == '"':
            end = i + 1
            chunk: list[str] = []
            while end < n and text[end] != '"':
                if text[end] == "\\" and end + 1 < n:
                    chunk.append(text[end + 1])
                    end += 2
                    continue
                chunk.append(text[end])
                end += 1
            yield "".join(chunk)
            i = end + 1
        elif ch in "{}":
            yield ch
            i += 1
        else:
            end = i
            while end < n and text[end] not in " \t\r\n{}\"":
                end += 1
            yield text[i:end]
            i = end


def _str(node: Any, key: str) -> Optional[str]:
    if isinstance(node, dict):
        value = node.get(key)
        if isinstance(value, str):
            return value
    return None


# ── Steam ──────────────────────────────────────────────────────────────


def steam_roots() -> list[Path]:
    home = Path.home()
    candidates = [
        home / ".local/share/Steam",
        home / ".steam/steam",
        home / ".var/app/com.valvesoftware.Steam/.local/share/Steam",
    ]
    seen: list[Path] = []
    for candidate in candidates:
        try:
            real = candidate.resolve()
        except OSError:
            continue
        if real.is_dir() and real not in seen:
            seen.append(real)
    return seen


# The art Steam keeps for each game, for the revolver's launch card. Its library cache has had two layouts: flat files
# (<id>_header.jpg) and, since 2024, a folder per game (<id>/header.jpg, sometimes one level deeper).
ART_KINDS = {"header": "header", "hero": "library_hero", "logo": "logo", "capsule": "library_600x900"}


def steam_art(app_id: str, roots: Optional[list[Path]] = None) -> dict[str, str]:
    """{kind: path} for the art of one Steam game: header (460 x 215), hero (the wide banner), logo, capsule."""
    if not _STEAM_ID.match(app_id):
        return {}
    found: dict[str, str] = {}
    for root in roots if roots is not None else steam_roots():
        cache = root / "appcache" / "librarycache"
        for kind, stem in ART_KINDS.items():
            if kind in found:
                continue
            candidates = [cache / f"{app_id}_{stem}.jpg", cache / f"{app_id}_{stem}.png"]
            folder = cache / app_id
            if folder.is_dir():
                candidates += sorted(folder.glob(f"{stem}.*")) + sorted(folder.glob(f"*/{stem}.*"))
            for path in candidates:
                if path.is_file():
                    found[kind] = str(path)
                    break
    return found


def steam_libraries(root: Path) -> list[Path]:
    """Every library folder Steam knows about, including the default one."""
    libraries = [root]
    try:
        text = (root / "steamapps" / "libraryfolders.vdf").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return libraries
    folders = parse_vdf(text).get("libraryfolders", {})
    if isinstance(folders, dict):
        for entry in folders.values():
            path = _str(entry, "path")
            if path:
                candidate = Path(path) / "steamapps"
                if candidate.is_dir() and Path(path) not in libraries:
                    libraries.append(Path(path))
    return libraries


#: Steam installs tools, runtimes and DLC alongside games. None of them
#: belong on a drum of things to play.
_NOT_GAMES = re.compile(
    r"^(steam (linux runtime|proton)|proton|steamworks|steam controller|"
    r"steamvr|steam ?deck|redistributables?)\b",
    re.IGNORECASE,
)


def steam_games(root: Path, now: float) -> list[Chamber]:
    games: list[Chamber] = []
    for library in steam_libraries(root):
        for manifest in sorted((library / "steamapps").glob("appmanifest_*.acf")):
            try:
                node = parse_vdf(manifest.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                continue
            state = node.get("AppState", {})
            appid = _str(state, "appid")
            name = _str(state, "name")
            if not appid or not name or not _STEAM_ID.match(appid):
                continue
            if _NOT_GAMES.match(name.strip()):
                continue
            last = _str(state, "LastPlayed")
            last_played = float(last) if last and last.isdigit() and int(last) > 0 else None
            games.append(Chamber(id=appid, name=name.strip(), source="steam", weight=1.0, last_played=last_played))
    return games


# ── PrismLauncher ──────────────────────────────────────────────────────


def prism_root() -> Optional[Path]:
    home = Path.home()
    for candidate in (
        home / ".local/share/PrismLauncher/instances",
        home / ".var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances",
    ):
        if candidate.is_dir():
            return candidate
    return None


def _read_cfg(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            key, sep, value = line.partition("=")
            if sep:
                values[key.strip()] = value.strip()
    except OSError:
        pass
    return values


def prism_instances(root: Path) -> list[Chamber]:
    instances: list[Chamber] = []
    for folder in sorted(p for p in root.iterdir() if p.is_dir()):
        if not _INSTANCE_ID.match(folder.name):
            continue
        cfg = _read_cfg(folder / "instance.cfg")
        name = cfg.get("name") or folder.name
        last = cfg.get("lastLaunchTime", "")
        last_played = int(last) / 1000.0 if last.isdigit() and int(last) > 0 else None
        instances.append(Chamber(id=folder.name, name=name, source="prismlauncher", weight=1.0, last_played=last_played))
    return instances


# ── Weights ────────────────────────────────────────────────────────────


def weight(mode: str, last_played: Optional[float], now: float) -> float:
    """How likely a game is to come up, relative to the others."""
    if mode == "random":
        return 1.0
    days = None if last_played is None else max(0.0, (now - last_played) / DAY)
    if mode == "recent":
        if days is None:
            return 1.0
        return 1.0 + 2.0 * max(0.0, 30.0 - days)
    if mode == "recommended":
        # A bell curve in time since last played, centred near four months:
        # yesterday is fine, a game you have forgotten is fine, and the
        # months in between are the least likely to be picked.
        if days is None:
            return 1.5
        centre, spread = 120.0, 90.0
        bell = math.exp(-((days - centre) ** 2) / (2 * spread**2))
        return 1.0 + 1.5 * (1.0 - bell) + 0.5 * math.exp(-days / 2.0)
    raise ValueError(f"unknown mode {mode!r}")


def pool(source: str, mode: str = "recent", *, now: Optional[float] = None) -> list[Chamber]:
    """The chambers for a source, weighted by a mode. Empty when nothing is found."""
    if source not in SOURCES:
        raise ValueError(f"unknown source {source!r}")
    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}")
    now = time.time() if now is None else now

    chambers: list[Chamber] = []
    if source == "steam":
        for root in steam_roots():
            chambers.extend(steam_games(root, now))
    else:
        root = prism_root()
        if root is not None:
            chambers.extend(prism_instances(root))

    seen: set[str] = set()
    unique: list[Chamber] = []
    for chamber in chambers:
        key = f"{chamber.source}:{chamber.id}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(Chamber(
            id=chamber.id,
            name=chamber.name,
            source=chamber.source,
            weight=weight(mode, chamber.last_played, now),
            last_played=chamber.last_played,
        ))
    unique.sort(key=lambda c: c.name.lower())
    return unique


def draw(chambers: list[Chamber], rng: Optional[random.Random] = None) -> Optional[Chamber]:
    """One chamber, chosen in proportion to its weight."""
    if not chambers:
        return None
    rng = rng or random.Random()
    return rng.choices(chambers, weights=[c.weight for c in chambers], k=1)[0]


# ── Launching ──────────────────────────────────────────────────────────


class LaunchError(ValueError):
    """The request was refused. Nothing was run."""


def launch_argv(source: str, game_id: str) -> list[str]:
    """The argument list that starts a game. Validated, and never a shell string."""
    if source == "steam":
        if not _STEAM_ID.match(game_id):
            raise LaunchError("a Steam id is a number")
        return ["xdg-open", f"steam://rungameid/{game_id}"]
    if source == "prismlauncher":
        if not _INSTANCE_ID.match(game_id):
            raise LaunchError("that instance name is not allowed")
        return ["prismlauncher", "--launch", game_id]
    raise LaunchError(f"unknown source {source!r}")


def fire(source: str, game_id: str, *, runner: Callable[[list[str]], Any] | None = None) -> list[str]:
    """Start the game. Returns the argv that was run."""
    argv = launch_argv(source, game_id)
    if runner is None:
        import subprocess

        subprocess.Popen(  # noqa: S603 - argv is fixed and validated above
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    else:
        runner(argv)
    return argv
