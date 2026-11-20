#!/usr/bin/env python3
"""halcyon fonts: install fonts for your user, and open Font Manager.

    halcyon fonts                        the fonts installed this way
    halcyon fonts install FILE...        .ttf .otf .ttc .woff .woff2 files, or a .zip of them (a family as the foundry
                                         ships it); each lands in ~/.local/share/fonts/halcyon-imported/NAME
    halcyon fonts install right-font     RightFont, "the most confusing font possible" (Right of the Bell), which
                                         Halcyon ships; --latest fetches the newest from rightofthebell.com/fonts
    halcyon fonts remove NAME            take an installed one away again
    halcyon fonts manager                open Font Manager (font-manager): preview, enable and disable, collections

Only right-font --latest downloads anything: everything else installs files you give it. RightFont is made from Inter
and Open Sans, and is under the SIL Open Font License like them (OFL.txt next to it).
"""

from __future__ import annotations

import json
import os
import urllib.request
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

DATA = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
FONTS = DATA / "fonts/halcyon-imported"
EXTENSIONS = {".ttf", ".otf", ".ttc", ".woff", ".woff2"}
# A zip of a family can be large, but never this large: that is a bomb, not fonts.
MAX_UNPACKED = 1024 * 1024 * 1024
# RightFont: shipped in ~/.local/share/fonts/halcyon-rightfont, and published on the site of the channel that made it.
RIGHT_FONT_DIR = DATA / "fonts/halcyon-rightfont"
RIGHT_FONT_FILE = "RightFont-Review-v7.ttf"
RIGHT_FONT_SITE = "https://www.rightofthebell.com"
# The repository's copy, for a run from a checkout (the installed one is in RIGHT_FONT_DIR).
BUNDLED_RIGHT_FONT = Path(__file__).resolve().parents[4] / ".local/share/fonts/halcyon-rightfont"


class FontError(Exception):
    pass


def safe_name(text: str) -> str:
    """A folder name from a file name: letters, digits, dashes."""
    name = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return name or "font"


def refresh_cache() -> None:
    if shutil.which("fc-cache"):
        subprocess.run(["fc-cache", "-f", str(FONTS)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       check=False, timeout=120)


def install_zip(path: Path) -> tuple[str, int]:
    """The font files in a zip, flattened into one folder named after it. Nothing outside it is written."""
    target = FONTS / safe_name(path.stem)
    count = 0
    try:
        with zipfile.ZipFile(path) as archive:
            members = [m for m in archive.infolist()
                       if not m.is_dir() and Path(m.filename).suffix.lower() in EXTENSIONS
                       and not Path(m.filename).name.startswith(".") and "__MACOSX" not in m.filename]
            if sum(m.file_size for m in members) > MAX_UNPACKED:
                raise FontError(f"{path.name} unpacks to more than 1 GiB; not installing it")
            target.mkdir(parents=True, exist_ok=True)
            for member in members:
                # Only the file's own name is kept, so a "../" in the zip can never leave the folder.
                dest = target / Path(member.filename).name
                with archive.open(member) as src, open(dest, "wb") as out:
                    shutil.copyfileobj(src, out)
                count += 1
    except zipfile.BadZipFile as error:
        raise FontError(f"{path.name} is not a zip that can be read: {error}") from error
    if count == 0:
        if target.exists() and not any(target.iterdir()):
            target.rmdir()
        raise FontError(f"{path.name} has no font files in it (.ttf .otf .ttc .woff .woff2)")
    return target.name, count


def install_file(path: Path) -> tuple[str, int]:
    target = FONTS / safe_name(path.stem.split("-")[0] or path.stem)
    target.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, target / path.name)
    return target.name, 1


def install(paths: list[Path]) -> list[tuple[str, int]]:
    done = []
    for path in paths:
        if not path.is_file():
            raise FontError(f"{path} does not exist")
        suffix = path.suffix.lower()
        if suffix == ".zip":
            done.append(install_zip(path))
        elif suffix in EXTENSIONS:
            done.append(install_file(path))
        else:
            raise FontError(f"{path.name}: not a font or a zip of fonts")
    refresh_cache()
    return done


def fetch(url: str, limit: int = 8 * 1024 * 1024) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "Halcyon-fonts"})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise FontError(f"{url} is larger than expected")
    return data


def latest_right_font_url() -> str:
    """The site is a script app: its fonts page loads FontLab-*.js, which names the font's current file."""
    page = fetch(f"{RIGHT_FONT_SITE}/fonts").decode("utf-8", "replace")
    main = re.search(r'src="(/assets/index-[^"]+\.js)"', page)
    if not main:
        raise FontError("the fonts page has changed; get RightFont from https://www.rightofthebell.com/fonts")
    script = fetch(RIGHT_FONT_SITE + main.group(1)).decode("utf-8", "replace")
    lab = re.search(r'"\./(FontLab-[A-Za-z0-9_-]+\.js)"', script)
    if not lab:
        raise FontError("the fonts page has changed; get RightFont from https://www.rightofthebell.com/fonts")
    code = fetch(f"{RIGHT_FONT_SITE}/assets/{lab.group(1)}").decode("utf-8", "replace")
    font = re.search(r'"(/assets/RightFont[A-Za-z0-9_.-]*\.(?:ttf|otf))"', code)
    if not font:
        raise FontError("no RightFont file on the fonts page now; see https://www.rightofthebell.com/fonts")
    return RIGHT_FONT_SITE + font.group(1)


def install_right_font(latest: bool = False) -> str:
    RIGHT_FONT_DIR.mkdir(parents=True, exist_ok=True)
    if latest:
        url = latest_right_font_url()
        data = fetch(url)
        if data[:4] not in (b"\x00\x01\x00\x00", b"OTTO", b"true"):
            raise FontError(f"{url} is not a font")
        (RIGHT_FONT_DIR / RIGHT_FONT_FILE).write_bytes(data)
        where = url
    else:
        source = next((d for d in (RIGHT_FONT_DIR, BUNDLED_RIGHT_FONT) if (d / RIGHT_FONT_FILE).is_file()), None)
        if source is None:
            raise FontError("Halcyon's copy of RightFont is missing; try: halcyon fonts install right-font --latest")
        for name in (RIGHT_FONT_FILE, "OFL.txt", "README.md"):
            if (source / name).is_file() and source != RIGHT_FONT_DIR:
                shutil.copyfile(source / name, RIGHT_FONT_DIR / name)
        where = str(source)
    if shutil.which("fc-cache"):
        subprocess.run(["fc-cache", "-f", str(RIGHT_FONT_DIR)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       check=False, timeout=120)
    return where


def installed() -> dict[str, list[str]]:
    if not FONTS.is_dir():
        return {}
    return {folder.name: sorted(f.name for f in folder.iterdir() if f.suffix.lower() in EXTENSIONS)
            for folder in sorted(FONTS.iterdir()) if folder.is_dir()}


def remove(name: str) -> None:
    folder = FONTS / safe_name(name)
    if not folder.is_dir():
        raise FontError(f"no installed font '{name}' (halcyon fonts lists them)")
    shutil.rmtree(folder)
    refresh_cache()


def open_detached(argv: list[str]) -> bool:
    if not shutil.which(argv[0]):
        return False
    subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)
    return True


def main(argv: list[str]) -> int:
    try:
        if not argv or argv[0] in ("list", "--json"):
            fonts = installed()
            if "--json" in argv:
                print(json.dumps(fonts, indent=2))
            elif not fonts:
                print(f"No fonts installed with halcyon fonts yet (they go in {FONTS}).")
            else:
                for name, files in fonts.items():
                    print(f"{name}  ({len(files)} file{'s' if len(files) != 1 else ''})")
            return 0
        if argv[0] == "install":
            if argv[1:2] == ["right-font"]:
                where = install_right_font(latest="--latest" in argv[2:])
                print(f'RightFont ("RightFont Review") is in {RIGHT_FONT_DIR}, from {where}. Good luck reading it.')
                return 0
            if len(argv) < 2:
                raise FontError("usage: halcyon fonts install FILE... | right-font [--latest]")
            for name, count in install([Path(p).expanduser() for p in argv[1:]]):
                print(f"installed {name}: {count} file{'s' if count != 1 else ''} in {FONTS / name}")
            return 0
        if argv[0] == "remove" and len(argv) == 2:
            remove(argv[1])
            print(f"removed {argv[1]}")
            return 0
        if argv[0] == "manager":
            if not open_detached(["font-manager"]):
                raise FontError("Font Manager is not installed (pacman -S font-manager)")
            return 0
        print(__doc__.strip())
        return 2
    except FontError as error:
        print(f"halcyon fonts: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
