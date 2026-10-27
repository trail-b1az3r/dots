#!/usr/bin/env python3
"""The animated wallpapers the anime themes use: `halcyon wallpapers`.

    halcyon wallpapers                  the wallpapers, and which are on this machine
    halcyon wallpapers get ID [--4k]    download one to ~/.local/share/halcyon/wallpapers
    halcyon wallpapers import ID FILE   put a file you downloaded yourself in its place
    halcyon wallpapers path ID          where the theme looks for it

The videos are other people's work and are not part of this repository. A theme that uses one works without it
(the colours apply, the current wallpaper stays); `get` or `import` brings the picture. Each entry names its
artist and its page, which is where to say thank you.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

HOME = Path.home()
DATA = Path(os.environ.get("XDG_DATA_HOME") or HOME / ".local/share")
DIRECTORY = DATA / "halcyon/wallpapers"

MAX_BYTES = 800 * 1024 * 1024
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0"

# `url` is a direct download that needs no account or click-through; an entry without one is imported by hand,
# because its site hands the file out only from the page (a signed link made for the visit).
CATALOG = {
    "after-icey": {
        "title": "After ICEY",
        "theme": "after-icey",
        "credit": "fan art, as published on MotionBGs",
        "page": "https://motionbgs.com/after-icey",
        "file": "after-icey.mp4",
        "url": "https://motionbgs.com/dl/hd/10303",
        "url_4k": "https://motionbgs.com/dl/4k/10303",
    },
    "silence": {
        "title": "Silence",
        "theme": "silence",
        "credit": "artist unknown, as published on wallhaven",
        "page": "https://wallhaven.cc/w/6ll7dx",
        "file": "silence.png",
        "url": "https://w.wallhaven.cc/full/6l/wallhaven-6ll7dx.png",
        "kind": "image",
    },
    "anime-girl-cat": {
        "title": "Anime Girl x Cat",
        "theme": "manga-ink",
        "credit": "fw_storm, as published on DesktopHut",
        "page": "https://www.desktophut.com/anime-girl-x-cat-pl2s",
        "file": "anime-girl-x-cat.mp4",
        "url": None,
    },
}


class WallpaperError(Exception):
    pass


def target(entry_id: str) -> Path:
    return DIRECTORY / CATALOG[entry_id]["file"]


def entry_for(entry_id: str) -> dict:
    if entry_id not in CATALOG:
        raise WallpaperError(f"no wallpaper called '{entry_id}'. They are: {', '.join(CATALOG)}")
    return CATALOG[entry_id]


def looks_like_video(head: bytes) -> bool:
    """MP4/MOV carry 'ftyp' at byte 4; WebM and Matroska start with the EBML marker."""
    return head[4:8] == b"ftyp" or head[:4] == b"\x1a\x45\xdf\xa3"


def status() -> list[dict]:
    rows = []
    for entry_id, entry in CATALOG.items():
        path = target(entry_id)
        rows.append({
            "id": entry_id, "title": entry["title"], "theme": entry["theme"], "credit": entry["credit"],
            "page": entry["page"], "path": str(path), "installed": path.is_file(),
            "downloadable": bool(entry.get("url")),
        })
    return rows


def looks_like_image(head: bytes) -> bool:
    """PNG, JPEG or WebP."""
    return head[:8] == b"\x89PNG\r\n\x1a\n" or head[:3] == b"\xff\xd8\xff" or (head[:4] == b"RIFF" and head[8:12] == b"WEBP")


def install(entry_id: str, source: Path) -> Path:
    """Put a checked file in place. The old one stays until the new one is complete."""
    image = CATALOG[entry_id].get("kind") == "image"
    with source.open("rb") as handle:
        head = handle.read(16)
    if image and not looks_like_image(head):
        raise WallpaperError(f"{source} is not an image (PNG, JPEG or WebP). A site's own page, saved by mistake, looks like this")
    if not image and not looks_like_video(head):
        raise WallpaperError(f"{source} is not a video (MP4 or WebM). A site's own page, saved by mistake, looks like this")
    destination = target(entry_id)
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.with_name(destination.name + ".part")
    shutil.copyfile(source, staging)
    os.replace(staging, destination)
    return destination


def download(entry_id: str, want_4k: bool = False) -> Path:
    entry = entry_for(entry_id)
    url = entry.get("url_4k") if want_4k and entry.get("url_4k") else entry.get("url")
    if not url:
        raise WallpaperError(
            f"{entry['title']} is not downloaded from here: {entry['page']} hands the file out from the page.\n"
            f"Download it there, then: halcyon wallpapers import {entry_id} PATH-TO-THE-FILE")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Referer": entry["page"]})
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=DIRECTORY, prefix=".download-", delete=False) as out:
        temporary = Path(out.name)
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                size = 0
                while True:
                    chunk = response.read(1 << 16)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise WallpaperError(f"{url} is larger than {MAX_BYTES >> 20} MB; not saving it")
                    out.write(chunk)
        except (urllib.error.URLError, OSError) as error:
            temporary.unlink(missing_ok=True)
            raise WallpaperError(f"could not download {url}: {error}") from None
        except WallpaperError:
            temporary.unlink(missing_ok=True)
            raise
    try:
        return install(entry_id, temporary)
    finally:
        temporary.unlink(missing_ok=True)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="halcyon wallpapers", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command")
    listing = sub.add_parser("list")
    listing.add_argument("--json", action="store_true")
    get = sub.add_parser("get")
    get.add_argument("id")
    get.add_argument("--4k", dest="four_k", action="store_true")
    imp = sub.add_parser("import")
    imp.add_argument("id")
    imp.add_argument("file", type=Path)
    path = sub.add_parser("path")
    path.add_argument("id")
    args = parser.parse_args(argv or ["list"])

    try:
        if args.command == "list":
            rows = status()
            if args.json:
                print(json.dumps(rows, indent=2))
                return 0
            for row in rows:
                state = "installed" if row["installed"] else ("missing: `get` downloads it" if row["downloadable"] else "missing: `import` it")
                print(f"{row['id']:<16} {row['title']:<20} theme {row['theme']:<10} {state}")
                print(f"{'':<16} {row['credit']}: {row['page']}")
            return 0
        if args.command == "path":
            entry_for(args.id)
            print(target(args.id))
            return 0
        if args.command == "import":
            entry_for(args.id)
            if not args.file.is_file():
                raise WallpaperError(f"{args.file} is not a file")
            print(f"{install(args.id, args.file)}")
        elif args.command == "get":
            print(f"{download(args.id, args.four_k)}")
        print(f"Applying the theme now picks it up: halcyon apply {entry_for(args.id)['theme']}")
        return 0
    except WallpaperError as error:
        print(f"halcyon wallpapers: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
