#!/usr/bin/env python3
"""Extract text from the screen, the clipboard, or a file: `halcyon text`.

    halcyon text                  pick a region of the screen (as Super + Shift + X does)
    halcyon text --window         the focused window
    halcyon text --screen         the whole focused monitor
    halcyon text --clipboard      the image in the clipboard (a screenshot you copied)
    halcyon text FILE             an image (png, jpg, webp, ...) or a PDF

    --lang eng+deu      the Tesseract languages (default: every installed one, or eng)
    --print             print the text instead of copying it
    --join              join lines that were broken inside a paragraph
    --both              copy it and print it

The text is copied to the clipboard and a notification shows the start of it. PDFs with a text layer are read
directly (pdftotext); scanned PDFs are rendered page by page (pdftoppm) and read with Tesseract.
Needs: tesseract (and its language data), grim and slurp for the screen, wl-clipboard, and poppler for PDFs.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".gif", ".pbm", ".pgm", ".ppm"}


class TextError(Exception):
    pass


def need(tool: str, package: str) -> str:
    path = shutil.which(tool)
    if not path:
        raise TextError(f"{tool} is not installed (Arch: pacman -S {package})")
    return path


def run(argv: list[str], *, input_bytes: bytes | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(argv, input=input_bytes, capture_output=True, check=False)


# --- pure helpers (tested) ---------------------------------------------------------------------------------

def languages(listed: str, wanted: str | None) -> str:
    """The -l value: what was asked for, else every installed language (osd excluded), else eng."""
    if wanted:
        return wanted
    names = [line.strip() for line in listed.splitlines()[1:] if line.strip() and line.strip() not in ("osd", "equ")]
    return "+".join(names) if names else "eng"


def tidy(text: str, join: bool = False) -> str:
    """Trim trailing spaces and runs of blank lines; with join, rejoin lines broken inside a paragraph and words
    hyphenated across lines."""
    lines = [line.rstrip() for line in text.replace("\f", "\n").splitlines()]
    out: list[str] = []
    for line in lines:
        if not line and out and not out[-1]:
            continue
        out.append(line)
    text = "\n".join(out).strip("\n")
    if join:
        paragraphs = re.split(r"\n\s*\n", text)
        joined = []
        for para in paragraphs:
            para = re.sub(r"(\w)-\n(\w)", r"\1\2", para)
            para = re.sub(r"\s*\n\s*", " ", para)
            joined.append(para.strip())
        text = "\n\n".join(joined)
    return text


def window_geometry(active: dict) -> str | None:
    """grim's -g value for hyprctl activewindow -j output."""
    at, size = active.get("at"), active.get("size")
    if not (isinstance(at, list) and isinstance(size, list) and len(at) == 2 and len(size) == 2):
        return None
    if size[0] <= 0 or size[1] <= 0:
        return None
    return f"{at[0]},{at[1]} {size[0]}x{size[1]}"


def preview(text: str, limit: int = 120) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


# --- sources ----------------------------------------------------------------------------------------------

def capture(geometry: str | None, output: str | None, path: Path) -> None:
    grim = need("grim", "grim")
    argv = [grim]
    if geometry:
        argv += ["-g", geometry]
    elif output:
        argv += ["-o", output]
    argv.append(str(path))
    if run(argv).returncode != 0 or not path.exists():
        raise TextError("could not take the screenshot (grim failed)")


def pick_region() -> str:
    slurp = need("slurp", "slurp")
    result = run([slurp])
    if result.returncode != 0 or not result.stdout.strip():
        raise TextError("cancelled")
    return result.stdout.decode().strip()


def focused_output() -> str | None:
    result = run(["hyprctl", "monitors", "-j"]) if shutil.which("hyprctl") else None
    if not result or result.returncode != 0:
        return None
    try:
        monitors = json.loads(result.stdout)
    except ValueError:
        return None
    return next((m.get("name") for m in monitors if m.get("focused")), None)


def active_window() -> str:
    if not shutil.which("hyprctl"):
        raise TextError("hyprctl not found; --window needs Hyprland")
    result = run(["hyprctl", "activewindow", "-j"])
    try:
        geometry = window_geometry(json.loads(result.stdout or b"{}"))
    except ValueError:
        geometry = None
    if not geometry:
        raise TextError("no focused window")
    return geometry


def clipboard_image(path: Path) -> None:
    paste = need("wl-paste", "wl-clipboard")
    types = run([paste, "--list-types"]).stdout.decode().split()
    image_type = next((t for t in types if t.startswith("image/")), None)
    if not image_type:
        raise TextError("the clipboard has no image in it")
    data = run([paste, "--type", image_type]).stdout
    if not data:
        raise TextError("could not read the image from the clipboard")
    path.write_bytes(data)


def ocr_image(path: Path, langs: str) -> str:
    tesseract = need("tesseract", "tesseract tesseract-data-eng")
    result = run([tesseract, str(path), "stdout", "-l", langs])
    if result.returncode != 0:
        message = result.stderr.decode(errors="replace").strip().splitlines()
        raise TextError("tesseract failed: " + (message[-1] if message else "no output"))
    return result.stdout.decode(errors="replace")


def pdf_text(path: Path, langs: str, workdir: Path) -> str:
    if shutil.which("pdftotext"):
        result = run(["pdftotext", "-layout", str(path), "-"])
        text = result.stdout.decode(errors="replace")
        if result.returncode == 0 and text.strip():
            return text
    # No text layer: a scan. Render each page and read it.
    need("pdftoppm", "poppler")
    if run(["pdftoppm", "-r", "300", "-png", str(path), str(workdir / "page")]).returncode != 0:
        raise TextError(f"could not render {path}")
    pages = sorted(workdir.glob("page*.png"))
    if not pages:
        raise TextError(f"{path} has no pages")
    return "\n\n".join(ocr_image(page, langs) for page in pages)


def copy(text: str) -> None:
    clip = need("wl-copy", "wl-clipboard")
    if run([clip], input_bytes=text.encode()).returncode != 0:
        raise TextError("could not copy to the clipboard")


def notify(summary: str, body: str) -> None:
    if shutil.which("notify-send"):
        subprocess.run(["notify-send", "-a", "Halcyon", "-i", "edit-copy", summary, body], check=False)


def extract(args: argparse.Namespace, workdir: Path) -> str:
    listed = run([need("tesseract", "tesseract tesseract-data-eng"), "--list-langs"]).stdout.decode(errors="replace") \
        if not args.lang else ""
    langs = languages(listed, args.lang)
    if args.file:
        path = Path(args.file).expanduser()
        if not path.is_file():
            raise TextError(f"{path} does not exist")
        if path.suffix.lower() == ".pdf":
            return pdf_text(path, langs, workdir)
        if path.suffix.lower() not in IMAGE_SUFFIXES:
            raise TextError(f"{path.suffix or path.name} is not an image or a PDF")
        return ocr_image(path, langs)
    shot = workdir / "shot.png"
    if args.clipboard:
        clipboard_image(shot)
    elif args.window:
        capture(active_window(), None, shot)
    elif args.screen:
        capture(None, focused_output(), shot)
    else:
        capture(pick_region(), None, shot)
    return ocr_image(shot, langs)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="halcyon text", description=__doc__.splitlines()[0])
    parser.add_argument("file", nargs="?", help="an image or PDF to read instead of the screen")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--window", action="store_true", help="the focused window")
    source.add_argument("--screen", action="store_true", help="the focused monitor")
    source.add_argument("--clipboard", action="store_true", help="the image in the clipboard")
    parser.add_argument("--lang", help="Tesseract languages, e.g. eng+deu")
    parser.add_argument("--join", action="store_true", help="join lines broken inside paragraphs")
    out = parser.add_mutually_exclusive_group()
    out.add_argument("--print", dest="print_only", action="store_true", help="print instead of copying")
    out.add_argument("--both", action="store_true", help="copy and print")
    args = parser.parse_args(argv)
    if args.file and (args.window or args.screen or args.clipboard):
        parser.error("give a FILE or a screen source, not both")

    try:
        with tempfile.TemporaryDirectory(prefix="halcyon-text-") as tmp:
            text = tidy(extract(args, Path(tmp)), join=args.join)
    except TextError as error:
        if str(error) == "cancelled":
            return 1
        print(f"halcyon text: {error}", file=sys.stderr)
        notify("No text extracted", str(error))
        return 1

    if not text:
        print("halcyon text: no text found", file=sys.stderr)
        notify("No text found", "Try a larger area, or --lang for another language.")
        return 1
    if args.print_only or args.both:
        print(text)
    if not args.print_only:
        try:
            copy(text)
        except TextError as error:
            print(f"halcyon text: {error}", file=sys.stderr)
            if not args.both:
                print(text)
            return 1
        notify("Text copied", preview(text))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
