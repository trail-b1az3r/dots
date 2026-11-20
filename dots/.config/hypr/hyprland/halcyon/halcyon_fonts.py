#!/usr/bin/env python3
"""halcyon fonts: install fonts for your user, and open Font Manager.

    halcyon fonts                        the fonts installed this way
    halcyon fonts install FILE...        .ttf .otf .ttc .woff .woff2 files, or a .zip of them (a family as the foundry
                                         ships it); each lands in ~/.local/share/fonts/halcyon-imported/NAME
    halcyon fonts install right-grotesk  Right Grotesk from your Downloads (the newest Right*Grotesk*.zip); with none
                                         there, opens the foundry's page to get it
    halcyon fonts remove NAME            take an installed one away again
    halcyon fonts manager                open Font Manager (font-manager): preview, enable and disable, collections

Fonts are only ever read from what you give it: nothing is downloaded. Right Grotesk is Pangram Pangram's, free to
try for personal use (the foundry emails it), and a licence is needed for commercial work: Halcyon cannot ship it.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

DATA = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
FONTS = DATA / "fonts/halcyon-imported"
EXTENSIONS = {".ttf", ".otf", ".ttc", ".woff", ".woff2"}
# A zip of a family can be large (Right Grotesk's is), but never this large: a bomb, not fonts.
MAX_UNPACKED = 1024 * 1024 * 1024
RIGHT_GROTESK_URL = "https://pangrampangram.com/products/right-grotesk"


class FontError(Exception):
    pass


def downloads() -> Path:
    try:
        out = subprocess.run(["xdg-user-dir", "DOWNLOAD"], capture_output=True, text=True, timeout=5, check=False)
        path = out.stdout.strip()
        if out.returncode == 0 and path and path != str(Path.home()):
            return Path(path)
    except (OSError, subprocess.SubprocessError):
        pass
    return Path.home() / "Downloads"


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


def newest_right_grotesk() -> Path | None:
    folder = downloads()
    if not folder.is_dir():
        return None
    found = [p for p in folder.iterdir()
             if p.is_file() and p.suffix.lower() == ".zip" and re.search(r"right.?grotesk", p.name, re.I)]
    return max(found, key=lambda p: p.stat().st_mtime) if found else None


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
            if argv[1:] == ["right-grotesk"]:
                found = newest_right_grotesk()
                if found is None:
                    print(f"No Right Grotesk zip in {downloads()}. It is Pangram Pangram's: free to try for personal "
                          f"use (the foundry emails it), licensed for commercial work. Opening {RIGHT_GROTESK_URL}; "
                          "once the zip is in Downloads, run this again.")
                    open_detached(["xdg-open", RIGHT_GROTESK_URL])
                    return 1
                argv = ["install", str(found)]
            if len(argv) < 2:
                raise FontError("usage: halcyon fonts install FILE... | right-grotesk")
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
