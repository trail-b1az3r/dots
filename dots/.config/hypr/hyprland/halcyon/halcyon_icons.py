#!/usr/bin/env python3
"""Theme-specific application icon packs for Halcyon: `halcyon icons`.

    halcyon icons                      the packs, whether they are made, and the icon theme in use
    halcyon icons make icey|ink|ink-dark [--base THEME]   make (or remake) a pack
    halcyon icons apply icey|ink|ink-dark   make it if needed and use it (the icon theme in use is remembered)
    halcyon icons restore              go back to the icon theme used before
    halcyon icons --json

Each pack is made on this computer from the icons you already have, so it covers every app installed, not only a
list someone drew by hand: each app's own icon is redrawn in the theme's style and set in the theme's frame.
Alacritty gets a purpose-drawn terminal mark, and iconless apps get a Halcyon generic application fallback.

    icey      After ICEY: cyan hexagon and gold mark
    ink       Manga Ink: paper disc, ink ring and screentone
    ink-dark  Manga Ink Dark: Manga Ink in negative
    hyperneo  Ember and neon macOS-style tile
    hsr       Star Rail: astral gold and lavender orbit
    fractured-glass / shattered-glass  Two distinct glass-shard designs
    red-sun   Ember-red solar horizon
    silence   Minimal black disc with red accents

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
    "hyperneo": {"theme": "Halcyon-HyperNeo", "name": "Halcyon HyperNeo"},
    "hsr": {"theme": "Halcyon-Star-Rail", "name": "Halcyon Star Rail"},
    "fractured-glass": {"theme": "Halcyon-Fractured-Glass", "name": "Halcyon Fractured Glass"},
    "red-sun": {"theme": "Halcyon-Red-Sun", "name": "Halcyon Red Sun"},
    "shattered-glass": {"theme": "Halcyon-Shattered-Glass", "name": "Halcyon Shattered Glass"},
    "silence": {"theme": "Halcyon-Silence", "name": "Halcyon Silence"},
}
# Every built-in Halcyon theme gets its own generated icon pack.
THEME_PACKS = {
    "after-icey": "icey",
    "manga-ink": "ink",
    "manga-ink-dark": "ink-dark",
    "hyperneo": "hyperneo",
    "hsr": "hsr",
    "fractured-glass": "fractured-glass",
    "red-sun": "red-sun",
    "shattered-glass": "shattered-glass",
    "silence": "silence",
}

# These are drawn by Halcyon rather than recoloured from the current icon
# theme. The application-x-executable names are the desktop-spec fallback
# used when an application has no Icon= entry or its icon cannot be found.
CUSTOM_ICONS = {
    "alacritty", "Alacritty",
    "application-x-executable", "application-default-icon", "application-x-desktop",
}

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
    if pack in ("ink", "ink-dark"):
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
    if pack == "hyperneo":
        return """<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">
  <rect x="7" y="7" width="114" height="114" rx="34" fill="#21100F" stroke="#FF9A5C" stroke-width="3"/>
  <rect x="15" y="15" width="98" height="98" rx="27" fill="none" stroke="#E7BDAA" stroke-opacity=".55"/>
  <path d="M17 36h94" stroke="#FF9A5C" stroke-width="3"/>
  <circle cx="27" cy="26" r="3" fill="#FF9A5C"/><circle cx="39" cy="26" r="3" fill="#E7BDAA"/>
  <path d="M64 2v9m-4-5h8" stroke="#FF9A5C" stroke-width="2"/>
</svg>"""
    if pack == "hsr":
        return """<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">
  <circle cx="64" cy="64" r="57" fill="#10142B" stroke="#F2C879" stroke-width="3"/>
  <ellipse cx="64" cy="64" rx="48" ry="19" fill="none" stroke="#C8B8FF" stroke-width="2" transform="rotate(-35 64 64)"/>
  <path d="m64 13 7 20 20 7-20 7-7 20-7-20-20-7 20-7Z" fill="#F2C879"/>
  <circle cx="100" cy="30" r="4" fill="#C8B8FF"/>
</svg>"""
    if pack == "fractured-glass":
        return """<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">
  <path d="M64 4 116 37 105 99 64 124 12 91 19 30Z" fill="#101522" stroke="#9CC2FF" stroke-width="3"/>
  <path d="m64 4-4 48 56-15M60 52l45 47M60 52 12 91m48-39 4 72m0-72 52-15" fill="none" stroke="#D6E3FF" stroke-width="2"/>
  <path d="m60 52 18-21 9 31-27-10Z" fill="#9CC2FF" fill-opacity=".3"/>
</svg>"""
    if pack == "red-sun":
        return """<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">
  <rect x="5" y="5" width="118" height="118" rx="30" fill="#17101D" stroke="#FF4940" stroke-width="3"/>
  <circle cx="64" cy="57" r="34" fill="none" stroke="#FF6B6B" stroke-width="7"/>
  <path d="M17 88h94M28 99h72" stroke="#E8B4C6" stroke-width="3" stroke-linecap="round"/>
  <path d="M64 3v9m-5-5h10" stroke="#FF4940" stroke-width="2"/>
</svg>"""
    if pack == "shattered-glass":
        return """<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">
  <path d="M64 5 119 35 106 101 64 123 9 91 18 29Z" fill="#0D1720" stroke="#9ED8FF" stroke-width="3"/>
  <path d="m64 5-7 42 35 17-28 59m0-76-46-18m46 18 55-12M57 47 9 91m48-44 49 54" fill="none" stroke="#DEE8F0" stroke-width="2.5"/>
  <path d="m64 5 14 31-21 11Z" fill="#9ED8FF" fill-opacity=".45"/>
</svg>"""
    if pack == "silence":
        return """<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">
  <circle cx="64" cy="64" r="58" fill="#090708" stroke="#FF6B6B" stroke-width="2"/>
  <path d="M32 56h64M42 76h44" stroke="#EDE6E6" stroke-opacity=".8" stroke-width="2"/>
  <circle cx="46" cy="48" r="5" fill="#FF6B6B"/><circle cx="82" cy="48" r="5" fill="#FF6B6B"/>
</svg>"""
    raise IconError(f"no frame design for icon pack '{pack}'")


# How the app's icon is redrawn: ImageMagick operations on it, alpha kept.
def recolour(pack: str) -> list[str]:
    palettes = {
        "icey": ("#1A8FAD", "#F4FEFF"),
        "hyperneo": ("#B94E31", "#FFF0E8"),
        "hsr": ("#8C75D9", "#FFF0C2"),
        "fractured-glass": ("#527DBB", "#EAF3FF"),
        "red-sun": ("#A92E38", "#FFE0DA"),
        "shattered-glass": ("#477E9C", "#E8F7FF"),
        "silence": ("#B52E3A", "#F3E6E6"),
    }
    if pack == "ink-dark":
        dark, light = PAPER, "#202022"
    elif pack == "ink":
        dark, light = INK, "#FFFFFF"
    else:
        dark, light = palettes[pack]
    return ["-colorspace", "gray", "-level", "30%,88%", "+level-colors", dark + "," + light]


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
    # A terminal-specific icon plus a deliberate fallback for applications
    # whose desktop entries omit Icon= or point at an unavailable icon.
    names.update(CUSTOM_ICONS)
    return sorted(names)


def special_icon_svg(pack: str, name: str) -> str:
    """Draw a theme-specific terminal or generic application glyph."""
    terminal = name in ("alacritty", "Alacritty")
    designs = {
        "icey": ("#5CD6F2", "M20 30h88v68H20z M20 46h88 M40 61l17 12-17 12m29 0h22 M92 18l4 8 8 4-8 4-4 8-4-8-8-4 8-4Z",
                 "M20 30h88v68H20z M20 46h88 M39 61h18v18H39z M68 61h24v6H68z M68 75h18v5H68z M96 18l3 8 8 3-8 3-3 8-3-8-8-3 8-3Z"),
        "ink": ("M24 26h80v76H24z M24 45h80 M40 61l16 12-16 12m28 0h22 M94 18v18m-9-9h18",
                "M24 26h80v76H24z M24 45h80 M39 60h20v20H39z M68 60h22v6H68z M68 74h17v6H68z M96 18v18m-9-9h18"),
        "ink-dark": ("M18 22h92v84H18z M18 43h92 M38 59l18 13-18 13m30 0h25 M94 14v22m-11-11h22",
                     "M18 22h92v84H18z M18 43h92 M36 58h23v23H36z M68 58h25v7H68z M68 75h19v7H68z M94 14v22m-11-11h22"),
        "hyperneo": ("M18 30h92v70H18z M18 48h92 M40 63l14 11-14 11m27 0h24 M28 39h3m10 0h3",
                     "M18 30h92v70H18z M18 48h92 M37 62h20v20H37z M68 62h25v6H68z M68 76h18v6H68z M28 39h3m10 0h3"),
        "hsr": ("M20 29h88v70H20z M20 45h88 M41 61l16 12-16 12m29 0h20 M96 15l4 12 12 4-12 4-4 12-4-12-12-4 12-4Z",
                "M20 29h88v70H20z M20 45h88 M38 59h21v21H38z M68 59h24v6H68z M68 74h18v6H68z M96 15l4 12 12 4-12 4-4 12-4-12-12-4 12-4Z"),
        "fractured-glass": ("M20 28h88v72H20z M20 45h88 M41 60l17 13-17 13m29 0h20 M63 2l-8 26 17 12-12 19",
                            "M20 28h88v72H20z M20 45h88 M38 59h20v20H38z M68 59h24v6H68z M68 74h18v6H68z M63 2l-8 26 17 12-12 19"),
        "red-sun": ("M20 29h88v70H20z M20 46h88 M41 61l16 12-16 12m29 0h20 M64 7a18 18 0 1 0 0 36 18 18 0 0 0 0-36",
                    "M20 29h88v70H20z M20 46h88 M38 60h21v21H38z M68 60h24v6H68z M68 75h18v6H68z M64 7a18 18 0 1 0 0 36 18 18 0 0 0 0-36"),
        "shattered-glass": ("M20 28h88v72H20z M20 45h88 M41 61l16 12-16 12m29 0h20 M64 1l-8 45 30 16-22 38",
                            "M20 28h88v72H20z M20 45h88 M38 59h20v20H38z M68 59h24v6H68z M68 74h18v6H68z M64 1l-8 45 30 16-22 38"),
        "silence": ("M23 31h82v67H23z M23 47h82 M41 63l15 11-15 11m28 0h19 M42 24h8m28 0h8",
                    "M23 31h82v67H23z M23 47h82 M39 60h20v20H39z M68 60h22v6H68z M68 75h17v5H68z M42 24h8m28 0h8"),
    }
    accent, terminal_path, generic_path = designs[pack]
    path = terminal_path if terminal else generic_path
    width = "5" if pack == "ink-dark" else "4"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">
  <g fill="none" stroke="{accent}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round">
    <path d="{path}"/>
  </g>
</svg>'''


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
        custom_sources = {}
        for name in CUSTOM_ICONS:
            custom_svg = Path(tmp) / f"{name}.svg"
            custom_svg.write_text(special_icon_svg(pack, name), encoding="utf-8")
            custom_sources[name] = custom_svg
        svg.write_text(frame_svg(pack), encoding="utf-8")
        done = run([*tool, "-background", "none", str(svg), str(frame)])
        if done.returncode != 0:
            # No SVG delegate (rsvg-convert): ImageMagick's own SVG renderer draws these simple shapes.
            done = run([*tool, "-background", "none", f"msvg:{svg}", str(frame)])
        if done.returncode != 0:
            raise IconError(f"ImageMagick could not draw the frame: {done.stderr.strip()[:200]}")
        inner = 70 if pack == "icey" else 66
        for name in [*PLACES, *app_icons()]:
            source = custom_sources.get(name) or find_icon(name, order)
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
