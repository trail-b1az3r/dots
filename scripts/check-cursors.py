#!/usr/bin/env python3
"""Check the Halcyon Glass cursor theme is complete and well formed.

XCursor: every file in cursors/ (aliases are symlinks) must parse: header,
table of contents, and image chunks whose sizes and hotspots add up.
hyprcursor: every .hlc must be a zip whose meta.hl only names images it
contains, with hotspots in 0..1. Both halves must use the name halcyon-theme
applies, and both must cover the essential cursor names.
"""

import re
import struct
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THEME_DIR = ROOT / "dots/.local/share/icons/Halcyon-Glass"
TOOL = ROOT / "dots/.config/hypr/hyprland/halcyon/halcyon-theme"
ESSENTIAL = ["default", "left_ptr", "pointer", "hand2", "text", "xterm", "wait", "watch", "progress",
             "not-allowed", "grab", "grabbing", "ns-resize", "ew-resize", "nwse-resize", "nesw-resize",
             "all-scroll", "crosshair", "help", "col-resize", "row-resize"]


def check_xcursor(path):
    data = path.read_bytes()
    magic, header, _version, ntoc = struct.unpack_from("<4sIII", data, 0)
    if magic != b"Xcur" or header != 16 or ntoc == 0:
        return "bad header"
    for i in range(ntoc):
        kind, size, position = struct.unpack_from("<III", data, 16 + 12 * i)
        if kind != 0xFFFD0002:
            return f"toc entry {i} is not an image"
        chunk = struct.unpack_from("<IIIIIIIII", data, position)
        _hdr, ckind, csize, _ver, width, height, xhot, yhot, _delay = chunk
        if ckind != kind or csize != size or width != size or height != size:
            return f"image {i} does not match its table entry"
        if xhot >= width or yhot >= height:
            return f"image {i} hotspot outside the image"
        if position + 36 + width * height * 4 > len(data):
            return f"image {i} runs past the end of the file"
    return None


def main():
    problems = []
    cursors = THEME_DIR / "cursors"
    names = set()
    for path in sorted(cursors.iterdir()):
        names.add(path.name)
        if path.is_symlink() and not path.resolve().is_file():
            problems.append(f"cursors/{path.name}: broken symlink")
            continue
        error = check_xcursor(path)
        if error:
            problems.append(f"cursors/{path.name}: {error}")

    covered = set()
    for hlc in sorted((THEME_DIR / "hyprcursors").glob("*.hlc")):
        covered.add(hlc.stem)
        with zipfile.ZipFile(hlc) as archive:
            files = set(archive.namelist())
            if "meta.hl" not in files:
                problems.append(f"{hlc.name}: no meta.hl")
                continue
            for line in archive.read("meta.hl").decode().splitlines():
                key, _, value = (part.strip() for part in line.partition("="))
                if key in ("hotspot_x", "hotspot_y") and not 0 <= float(value) <= 1:
                    problems.append(f"{hlc.name}: {key} {value} outside 0..1")
                elif key == "define_size" and value.split(",")[1].strip() not in files:
                    problems.append(f"{hlc.name}: meta names missing image {value}")
                elif key == "define_override":
                    covered.add(value)

    for name in ESSENTIAL:
        if name not in names:
            problems.append(f"XCursor theme lacks '{name}'")
        if name not in covered:
            problems.append(f"hyprcursor theme lacks '{name}'")

    applied = re.search(r'^CURSOR_THEME = "([^"]+)"', TOOL.read_text(), re.M).group(1)
    manifest = re.search(r"^name = (.+)$", (THEME_DIR / "manifest.hl").read_text(), re.M).group(1).strip()
    index = re.search(r"^Name=(.+)$", (THEME_DIR / "index.theme").read_text(), re.M).group(1).strip()
    if not applied == manifest == index == THEME_DIR.name:
        problems.append(f"theme names disagree: tool {applied}, manifest {manifest}, index {index}, "
                        f"folder {THEME_DIR.name}")

    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        return 1
    print(f"ok: {len(names)} XCursor names, {len(covered)} hyprcursor names, theme '{applied}'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
