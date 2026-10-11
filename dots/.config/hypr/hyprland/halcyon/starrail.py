"""The Star Rail theme: characters fetched on request, kept in the cache.

Used by `halcyon-theme starrail`, which puts the chosen character on the
Star Rail theme's banner. Pure Python, standard library only.

Halcyon does not bundle any Honkai: Star Rail artwork or names. When the
user asks for them, this module downloads a public character index and
portraits from the StarRailRes data project into the cache directory, and
reads them from there afterwards. The data project is AGPL-3.0; its files
are not copied into this repository.

Network use is deliberate. It happens when the user runs
`halcyon starrail refresh`, or when they have turned on
`starRail.fetchCharacters` in Settings. Nothing is fetched otherwise, and
nothing about the user is sent: the requests are plain downloads of fixed
URLs.

Everything that touches the network goes through `_download`, so the
parts that decide what is trusted (size limits, file signatures, the shape
of the index) can be tested without a connection.
"""

from __future__ import annotations

import json
import os
import pathlib
import random
import tempfile
import time
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Optional


INDEX_URL = (
    "https://raw.githubusercontent.com/Mar-7th/StarRailRes/master/"
    "index_new/en/characters.json"
)
PORTRAIT_URL = (
    "https://raw.githubusercontent.com/Mar-7th/StarRailRes/master/"
    "icon/character/{id}.png"
)

#: The index is refreshed when it is older than this.
MAX_AGE_SECONDS = 7 * 24 * 3600

#: Larger than anything legitimate here; anything bigger is not what we asked for.
MAX_INDEX_BYTES = 4 * 1024 * 1024
MAX_PORTRAIT_BYTES = 2 * 1024 * 1024

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

#: One accent per element. These are Halcyon's own colours for the
#: elements, chosen to read on glass; they are not taken from any game.
ELEMENT_ACCENTS: dict[str, str] = {
    "Fire": "#FF6B4A",
    "Ice": "#7FD3FF",
    "Imaginary": "#F5D76E",
    "Physical": "#C9D1DC",
    "Quantum": "#8A7BFF",
    "Thunder": "#C77DFF",
    "Wind": "#6FE3B0",
}

Download = Callable[[str, int], bytes]


class StarRailError(RuntimeError):
    """Something could not be fetched or trusted. The message is user-facing."""


@dataclass(frozen=True)
class Character:
    id: str
    name: str
    element: str
    path: str
    rarity: int

    @property
    def accent(self) -> Optional[str]:
        return ELEMENT_ACCENTS.get(self.element)


def cache_dir() -> pathlib.Path:
    base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return pathlib.Path(base) / "halcyon" / "starrail"


def _index_file() -> pathlib.Path:
    return cache_dir() / "characters.json"


def _portrait_file(char_id: str) -> pathlib.Path:
    return cache_dir() / "portraits" / f"{char_id}.png"


def _state_file() -> pathlib.Path:
    return cache_dir() / "state.json"


# ── Downloading (the only network code) ────────────────────────────────


def _download(url: str, limit: int) -> bytes:
    """Fetch `url`, refusing anything larger than `limit` bytes."""
    request = urllib.request.Request(url, headers={"User-Agent": "halcyon-starrail"})  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310 - fixed URLs
            data = response.read(limit + 1)
    except Exception as exc:  # noqa: BLE001 - every failure becomes one clear message
        raise StarRailError(f"could not download {url.rsplit('/', 1)[-1]}: {exc.__class__.__name__}") from None
    if len(data) > limit:
        raise StarRailError("the download is larger than expected, so it was discarded")
    return data


# ── Validation ─────────────────────────────────────────────────────────


def parse_index(raw: bytes) -> dict[str, Character]:
    """Characters from the index, with anything malformed left out.

    A single bad entry must not hide the rest, but a document that is not
    an index at all is an error.
    """
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise StarRailError("the character index is not valid JSON") from None
    if not isinstance(data, dict) or not data:
        raise StarRailError("the character index is empty or not an object")

    characters: dict[str, Character] = {}
    for key, value in data.items():
        if not isinstance(value, dict):
            continue
        char_id = str(value.get("id", key))
        name = value.get("name")
        element = value.get("element")
        path = value.get("path")
        rarity = value.get("rarity")
        if not (char_id.isdigit() and isinstance(name, str) and name.strip()):
            continue
        # The player's own character is listed with a template placeholder
        # for its name, and it has no portrait to show.
        if "{" in name or "}" in name:
            continue
        if not isinstance(element, str) or not isinstance(path, str):
            continue
        characters[char_id] = Character(
            id=char_id,
            name=name.strip(),
            element=element,
            path=path,
            rarity=int(rarity) if isinstance(rarity, int) else 0,
        )
    if not characters:
        raise StarRailError("the character index holds no usable characters")
    return characters


def validate_portrait(raw: bytes) -> bytes:
    if len(raw) > MAX_PORTRAIT_BYTES:
        raise StarRailError("the portrait is larger than expected, so it was discarded")
    if not raw.startswith(PNG_SIGNATURE):
        raise StarRailError("the portrait is not a PNG image, so it was discarded")
    return raw


# ── The cache ──────────────────────────────────────────────────────────


def _write_atomic(path: pathlib.Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def index_age(now: float) -> Optional[float]:
    try:
        return now - _index_file().stat().st_mtime
    except OSError:
        return None


def refresh(
    *,
    force: bool = False,
    now: Callable[[], float] = time.time,
    download: Download = _download,
) -> int:
    """Make sure the character index is cached and recent. Returns the count."""
    age = index_age(now())
    if not force and age is not None and age < MAX_AGE_SECONDS:
        return len(load_characters())
    raw = download(INDEX_URL, MAX_INDEX_BYTES)
    characters = parse_index(raw)
    _write_atomic(_index_file(), raw)
    return len(characters)


def load_characters() -> dict[str, Character]:
    try:
        raw = _index_file().read_bytes()
    except OSError:
        return {}
    try:
        return parse_index(raw)
    except StarRailError:
        return {}


def portrait(char: Character, *, download: Download = _download) -> str:
    """The cached portrait path for `char`, fetching it first if needed."""
    target = _portrait_file(char.id)
    if target.is_file():
        return os.fspath(target)
    raw = validate_portrait(download(PORTRAIT_URL.format(id=char.id), MAX_PORTRAIT_BYTES))
    _write_atomic(target, raw)
    return os.fspath(target)


def _read_state() -> dict[str, Any]:
    try:
        data = json.loads(_state_file().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_state(state: dict[str, Any]) -> None:
    _write_atomic(_state_file(), json.dumps(state, indent=2).encode("utf-8"))


def current(characters: Optional[dict[str, Character]] = None) -> Optional[Character]:
    """The character the theme is showing, or None if none has been chosen."""
    characters = load_characters() if characters is None else characters
    char_id = str(_read_state().get("id", ""))
    return characters.get(char_id)


def choose_next(
    characters: Optional[dict[str, Character]] = None,
    *,
    rng: Optional[random.Random] = None,
) -> Optional[Character]:
    """Pick a different character from the last one, at random."""
    characters = load_characters() if characters is None else characters
    if not characters:
        return None
    rng = rng or random.Random()
    previous = current(characters)
    pool = sorted(characters)
    if previous is not None and len(pool) > 1:
        pool = [cid for cid in pool if cid != previous.id]
    chosen = characters[rng.choice(pool)]
    _write_state({"id": chosen.id, "chosenAt": int(time.time())})
    return chosen


def status() -> dict[str, Any]:
    """What the cache holds, for `status` and for the shell to read."""
    characters = load_characters()
    char = current(characters)
    age = index_age(time.time())
    return {
        "characters": len(characters),
        "indexAgeSeconds": int(age) if age is not None else None,
        "current": (
            {
                "id": char.id,
                "name": char.name,
                "element": char.element,
                "path": char.path,
                "rarity": char.rarity,
                "accent": char.accent,
                "portrait": os.fspath(_portrait_file(char.id)),
            }
            if char
            else None
        ),
    }
