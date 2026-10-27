#!/usr/bin/env python3
"""Icon packs for the anime themes: `halcyon icons`.

    halcyon icons                      the packs, whether they are made, and the icon theme in use
    halcyon icons make icey|ink|ink-dark [--base THEME]   make (or remake) a pack
    halcyon icons apply icey|ink|ink-dark   make it if needed and use it (the icon theme in use is remembered)
    halcyon icons restore              go back to the icon theme used before
    halcyon icons --json

Each pack is made on this computer from the icons you already have, so it covers every app installed, not only a
list someone drew by hand: each app's own icon is redrawn in the theme's style and set in the theme's frame.

    icey      After ICEY: a dark navy hexagon with a cyan rim and a gold mark, the icon in cyan light
    ink       Manga Ink: a paper disc in a thick ink ring with a hard shadow and screentone, the icon inked
    ink-dark  Manga Ink Dark: the same in negative, paper-white ink on black

Icons the pack doesn't redraw come from the theme it was made from (--base, by default the icon theme in use), so
nothing goes missing. The packs are written to ~/.local/share/icons/Halcyon-*; applying a Halcyon theme with an
icon pack uses it (Settings > Halcyon turns that off), and leaving the theme puts your icons back.

Needs ImageMagick (`magick`), which the shell already depends on.
"""

from __future__ import annotations

import argparse
import configparser
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HOME = Path.home()
DATA = Path(os.environ.get("XDG_DATA_HOME") or HOME / ".local/share")
STATE = Path(os.environ.get("XDG_STATE_HOME") or HOME / ".local/state") / "halcyon"
ICON_DIRS = [DATA / "icons", HOME / ".icons", Path("/usr/local/share/icons"), Path("/usr/share/icons")]
PIXMAPS = [Path("/usr/share/pixmaps")]
APP_DIRS = [DATA / "applications", Path("/usr/local/share/applications"), Path("/usr/share/applications"),
            Path("/var/lib/flatpak/exports/share/applications"), DATA / "flatpak/exports/share/applications"]
PREVIOUS = STATE / "icon-theme-before.txt"
SIZE = 128

PACKS = {
    "icey": {"theme": "Halcyon-After-ICEY", "name": "Halcyon After ICEY"},
    "ink": {"theme": "Halcyon-Manga-Ink", "name": "Halcyon Manga Ink"},
    "ink-dark": {"theme": "Halcyon-Manga-Ink-Dark", "name": "Halcyon Manga Ink Dark"},
}
# Which Halcyon theme uses which pack.
THEME_PACKS = {"after-icey": "icey", "manga-ink": "ink", "manga-ink-dark": "ink-dark"}

# Folders and the like, redrawn too, beside every app's icon.
PLACES = ["folder", "user-home", "user-desktop", "user-trash", "user-trash-full", "folder-documents",
          "folder-download", "folder-music", "folder-pictures", "folder-videos", "folder-templates", "folder-publicshare",
          "network-workgroup", "drive-harddisk", "drive-removable-media", "computer", "utilities-terminal",
          "system-file-manager", "preferences-system", "applications-games", "system-software-install", "web-browser"]

INK, PAPER = "#141414", "#F7F3EA"


class IconError(Exception):
    pass


def run(cmd: list[str], timeout: float = 60) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        return subprocess.CompletedProcess(cmd, 127, "", str(error))


def magick() -> list[str]:
    if shutil.which("magick"):
        return ["magick"]
    if shutil.which("convert"):
        return ["convert"]
    raise IconError("ImageMagick isn't installed (sudo pacman -S imagemagick)")


# --- the frames, drawn as SVG at 128 x 128 ----------------------------------------------------------------------------

def hexagon(cx: float, cy: float, r: float) -> str:
    import math
    points = [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in range(-90, 270, 60)]
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in points)


def frame_svg(pack: str) -> str:
    if pack == "icey":
        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{SIZE}" height="{SIZE}" viewBox="0 0 128 128">
  <defs><radialGradient id="g" cx="50%" cy="40%" r="60%">
    <stop offset="0" stop-color="#1B2A44"/><stop offset="1" stop-color="#080D18"/></radialGradient></defs>
  <polygon points="{hexagon(64, 64, 60)}" fill="url(#g)" stroke="#5CD6F2" stroke-width="3"/>
  <polygon points="{hexagon(64, 64, 52)}" fill="none" stroke="#5CD6F2" stroke-opacity="0.35" stroke-width="1.2"/>
  <path d="M 8 30 L 8 18 L 20 18 M 108 18 L 120 18 L 120 30 M 8 98 L 8 110 L 20 110 M 108 110 L 120 110 L 120 98"
        fill="none" stroke="#5CD6F2" stroke-width="2.4"/>
  <polygon points="64,1 68,5 64,9 60,5" fill="#FFD86B"/>
</svg>"""
    ink, paper = (PAPER, "#0D0D0E") if pack == "ink-dark" else (INK, PAPER)
    dots = []
    for row in range(0, 9):
        for col in range(0, 9):
            x, y = 64 + col * 6 + (row % 2) * 3, 64 + row * 6
            weight = min(1.0, (x - 64) / 50) * min(1.0, (y - 64) / 50)
            if weight > 0.08 and (x - 62) ** 2 + (y - 62) ** 2 < 50 ** 2:
                dots.append(f'<circle cx="{x}" cy="{y}" r="{0.4 + 1.9 * weight:.2f}"/>')
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{SIZE}" height="{SIZE}" viewBox="0 0 128 128">
  <circle cx="67" cy="67" r="56" fill="{ink}"/>
  <circle cx="62" cy="62" r="56" fill="{paper}" stroke="{ink}" stroke-width="6"/>
  <g fill="{ink}" fill-opacity="0.55">{''.join(dots)}</g>
</svg>"""


# How the app's icon is redrawn: ImageMagick operations on it, alpha kept.
def recolour(pack: str) -> list[str]:
    if pack == "icey":
        # Cyan light: dark parts navy-cyan, light parts near white.
        return ["-colorspace", "gray", "-level", "0%,88%", "+level-colors", "#1A8FAD,#F4FEFF"]
    if pack == "ink-dark":
        return ["-colorspace", "gray", "-level", "30%,75%", "+level-colors", f"{PAPER},#202022"]
    return ["-colorspace", "gray", "-level", "30%,75%", "+level-colors", f"{INK},#FFFFFF"]


# --- finding icons --------------------------------------------------------------------------------------------------

def current_icon_theme() -> str:
    if shutil.which("gsettings"):
        out = run(["gsettings", "get", "org.gnome.desktop.interface", "icon-theme"]).stdout.strip().strip("'")
        if out:
            return out
    return ""


def theme_dir(name: str) -> Path | None:
    for base in ICON_DIRS:
        if (base / name / "index.theme").is_file():
            return base / name
    return None


def inherits(name: str) -> list[str]:
    folder = theme_dir(name)
    if not folder:
        return []
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    try:
        parser.read(folder / "index.theme", encoding="utf-8")
        return [t.strip() for t in parser.get("Icon Theme", "Inherits", fallback="").split(",") if t.strip()]
    except (configparser.Error, OSError):
        return []


def search_order(base: str) -> list[Path]:
    order, seen, queue = [], set(), [base] if base else []
    while queue:
        name = queue.pop(0)
        if name in seen:
            continue
        seen.add(name)
        folder = theme_dir(name)
        if folder:
            order.append(folder)
            queue.extend(inherits(name))
    for fallback in ("hicolor", "Adwaita", "breeze", "Papirus"):
        folder = theme_dir(fallback)
        if folder and folder not in order:
            order.append(folder)
    return order


def size_rank(path: Path) -> int:
    """Prefer scalable, then the largest raster."""
    text = str(path)
    if "/scalable/" in text or path.suffix == ".svg":
        return 10000
    match = re.search(r"/(\d+)x\d+(@\d)?/", text) or re.search(r"/(\d+)/", text)
    return int(match.group(1)) if match else 0


def find_icon(name: str, order: list[Path]) -> Path | None:
    if os.path.isabs(name):
        path = Path(name)
        return path if path.is_file() else None
    for folder in order:
        found = [p for ext in ("svg", "png") for p in folder.glob(f"**/{name}.{ext}")
                 if "/symbolic" not in str(p) and "-symbolic" not in p.stem]
        if found:
            return max(found, key=size_rank)
    for folder in PIXMAPS:
        for ext in ("svg", "png", "xpm"):
            if (folder / f"{name}.{ext}").is_file():
                return folder / f"{name}.{ext}"
    return None


def app_icons() -> list[str]:
    names = set()
    for folder in APP_DIRS:
        if not folder.is_dir():
            continue
        for desktop in folder.glob("*.desktop"):
            try:
                text = desktop.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if re.search(r"^NoDisplay\s*=\s*true", text, re.M):
                continue
            match = re.search(r"^Icon\s*=\s*(.+)$", text, re.M)
            if match:
                icon = match.group(1).strip()
                if icon and not os.path.isabs(icon):
                    names.add(icon)
    return sorted(names)


# --- making a pack --------------------------------------------------------------------------------------------------

def pack_dir(pack: str) -> Path:
    return DATA / "icons" / PACKS[pack]["theme"]


def make(pack: str, base: str = "", quiet: bool = False) -> dict:
    if pack not in PACKS:
        raise IconError(f"no pack called '{pack}'. They are: {', '.join(PACKS)}")
    tool = magick()
    base = base or current_icon_theme()
    if base.startswith("Halcyon-"):
        base = read_previous() or ""
    order = search_order(base)
    out = pack_dir(pack)
    apps = out / f"{SIZE}x{SIZE}" / "apps"
    if apps.is_dir():
        for old in apps.glob("*.png"):
            old.unlink()
    apps.mkdir(parents=True, exist_ok=True)
    made, missing = 0, []
    with tempfile.TemporaryDirectory() as tmp:
        frame = Path(tmp) / "frame.png"
        svg = Path(tmp) / "frame.svg"
        svg.write_text(frame_svg(pack), encoding="utf-8")
        done = run([*tool, "-background", "none", str(svg), str(frame)])
        if done.returncode != 0:
            # No SVG delegate (rsvg-convert): ImageMagick's own SVG renderer draws these simple shapes.
            done = run([*tool, "-background", "none", f"msvg:{svg}", str(frame)])
        if done.returncode != 0:
            raise IconError(f"ImageMagick could not draw the frame: {done.stderr.strip()[:200]}")
        inner = 70 if pack == "icey" else 66
        for name in [*PLACES, *app_icons()]:
            source = find_icon(name, order)
            if not source:
                missing.append(name)
                continue
            target = apps / f"{name}.png"
            sources = [str(source)] + ([f"msvg:{source}"] if source.suffix == ".svg" else [])
            for reference in sources:
                command = [*tool, str(frame), "(", "-background", "none", "-density", "384", reference,
                           "-resize", f"{inner}x{inner}", *recolour(pack), ")",
                           "-gravity", "center", "-geometry", "-2-2" if pack != "icey" else "+0+0", "-composite",
                           str(target)]
                if run(command).returncode == 0 and target.is_file():
                    made += 1
                    break
            else:
                missing.append(name)
    write_index(pack, base)
    if shutil.which("gtk-update-icon-cache"):
        run(["gtk-update-icon-cache", "-f", "-t", str(out)])
    result = {"pack": pack, "theme": PACKS[pack]["theme"], "path": str(out), "base": base, "icons": made,
              "missing": len(missing)}
    if not quiet:
        print(f"made {PACKS[pack]['name']}: {made} icons from {base or 'hicolor'} ({out})")
    return result


def write_index(pack: str, base: str) -> None:
    inherit = ",".join(t for t in (base, "hicolor") if t)
    text = (f"[Icon Theme]\nName={PACKS[pack]['name']}\nComment=Made by Halcyon from {base or 'hicolor'}\n"
            f"Inherits={inherit}\nDirectories={SIZE}x{SIZE}/apps\n\n"
            f"[{SIZE}x{SIZE}/apps]\nSize={SIZE}\nMinSize=16\nMaxSize=512\nContext=Applications\nType=Scalable\n")
    (pack_dir(pack) / "index.theme").write_text(text, encoding="utf-8")


# --- using a pack ---------------------------------------------------------------------------------------------------

def read_previous() -> str:
    try:
        return PREVIOUS.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def set_icon_theme(name: str) -> None:
    """Through halcyon-theme, which sets GTK's, KDE's and Qt's (qt5ct, qt6ct) alike."""
    tool = Path(__file__).resolve().parent / "halcyon-theme"
    run([sys.executable, str(tool), "rules", "icons", "set", name])


def apply(pack: str) -> int:
    if not (pack_dir(pack) / "index.theme").is_file():
        make(pack)
    current = current_icon_theme()
    if current and not current.startswith("Halcyon-"):
        STATE.mkdir(parents=True, exist_ok=True)
        PREVIOUS.write_text(current + "\n", encoding="utf-8")
    set_icon_theme(PACKS[pack]["theme"])
    print(f"icons: {PACKS[pack]['name']}")
    return 0


def restore() -> int:
    current = current_icon_theme()
    previous = read_previous()
    if current.startswith("Halcyon-") and previous:
        set_icon_theme(previous)
        print(f"icons: back to {previous}")
    return 0


def status() -> dict:
    return {
        "current": current_icon_theme(),
        "before": read_previous(),
        "packs": [{"id": pack, "theme": info["theme"], "name": info["name"],
                   "made": (pack_dir(pack) / "index.theme").is_file()} for pack, info in PACKS.items()],
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="halcyon icons", description="Icon packs for the anime themes.")
    parser.add_argument("action", nargs="?", default="status", choices=("status", "make", "apply", "restore"))
    parser.add_argument("pack", nargs="?")
    parser.add_argument("--base", default="", help="make: the icon theme to redraw (default: the one in use)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.action in ("make", "apply"):
            if args.pack not in PACKS:
                raise IconError(f"which pack? {', '.join(PACKS)}")
            if args.action == "make":
                result = make(args.pack, args.base, quiet=args.json)
                if args.json:
                    print(json.dumps(result))
                return 0
            return apply(args.pack)
        if args.action == "restore":
            return restore()
        info = status()
        if args.json:
            print(json.dumps(info, indent=2))
            return 0
        print(f"icon theme in use: {info['current'] or '(unknown)'}")
        for pack in info["packs"]:
            print(f"  {pack['id']:<9} {pack['name']:<24} {'made' if pack['made'] else 'not made yet'}")
        return 0
    except IconError as error:
        print(f"halcyon icons: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
