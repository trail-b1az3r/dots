"""Deriving a palette from the wallpaper.

Two extraction paths, tried in order:

1. ImageMagick, when it is installed. Downscaling and quantising in C is
   an order of magnitude faster than anything Python can do, and it reads
   every format the user is likely to set as a wallpaper.
2. A small pure-Python PNG reader. It exists so a machine without
   ImageMagick still gets wallpaper colours instead of a flat fallback.

Whichever path runs, the result is the same: a list of (hex, weight)
swatches, from which `derive` picks a seed and builds the palette.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import struct
import subprocess
import zlib
from dataclasses import dataclass, field
from typing import Any

from . import color

Swatch = tuple[color.RGB, float]


@dataclass
class Palette:
    """The colours a wallpaper contributes to the theme."""

    seed: color.RGB
    accent: color.RGB
    secondary: color.RGB
    tertiary: color.RGB
    neutral: color.RGB
    source: str = "fallback"
    swatches: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "seed": color.to_hex(self.seed),
            "accent": color.to_hex(self.accent),
            "secondary": color.to_hex(self.secondary),
            "tertiary": color.to_hex(self.tertiary),
            "neutral": color.to_hex(self.neutral),
            "swatches": list(self.swatches),
        }


# ── Extraction ─────────────────────────────────────────────────────────


def _imagemagick_binary() -> list[str] | None:
    if shutil.which("magick"):
        return ["magick"]
    if shutil.which("convert"):
        # ImageMagick 6 ships `convert` without the `magick` dispatcher.
        return ["convert"]
    return None


_HISTOGRAM_RE = re.compile(r"^\s*(\d+):\s*\([^)]*\)\s+(#[0-9A-Fa-f]{6,8})")


def _extract_imagemagick(path: str, colors: int = 24) -> list[Swatch]:
    binary = _imagemagick_binary()
    if binary is None:
        return []

    argv = [
        *binary,
        f"{path}[0]",          # first frame; animated wallpapers are legal
        "-resize", "128x128^",
        "-alpha", "off",
        "-colors", str(colors),
        "-format", "%c",
        "histogram:info:-",
    ]
    try:
        completed = subprocess.run(
            argv, capture_output=True, text=True, timeout=20, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if completed.returncode != 0:
        return []

    swatches: list[Swatch] = []
    for line in completed.stdout.splitlines():
        match = _HISTOGRAM_RE.match(line)
        if not match:
            continue
        count, hex_value = match.groups()
        try:
            swatches.append((color.parse_hex(hex_value), float(count)))
        except ValueError:
            continue
    return swatches


def _extract_png(path: str, max_samples: int = 20000) -> list[Swatch]:
    """Minimal PNG decoder covering the 8-bit colour types.

    Deliberately narrow: this is a fallback, not an image library. Any
    format it does not understand returns no swatches and the caller
    falls back to the configured accent.
    """
    try:
        with open(path, "rb") as handle:
            data = handle.read()
    except OSError:
        return []

    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return []

    width = height = depth = ctype = 0
    idat = bytearray()
    plte = b""
    offset = 8
    while offset + 8 <= len(data):
        (length,) = struct.unpack(">I", data[offset:offset + 4])
        chunk = data[offset + 4:offset + 8]
        payload = data[offset + 8:offset + 8 + length]
        offset += 12 + length
        if chunk == b"IHDR":
            width, height, depth, ctype = struct.unpack(">IIBB", payload[:10])
        elif chunk == b"PLTE":
            plte = payload
        elif chunk == b"IDAT":
            idat += payload
        elif chunk == b"IEND":
            break

    if depth != 8 or width == 0 or height == 0:
        return []
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(ctype)
    if channels is None:
        return []

    try:
        raw = zlib.decompress(bytes(idat))
    except zlib.error:
        return []

    stride = width * channels
    if len(raw) < height * (stride + 1):
        return []

    # Sample rows rather than unfiltering the whole image: filters are
    # row-relative, so we still have to walk every row, but we only need
    # to bucket a fraction of the pixels.
    previous = bytearray(stride)
    counts: dict[tuple[int, int, int], float] = {}
    pixel_step = max(1, (width * height) // max_samples)

    position = 0
    for _ in range(height):
        filter_type = raw[position]
        position += 1
        line = bytearray(raw[position:position + stride])
        position += stride
        _unfilter_row(filter_type, line, previous, channels)
        previous = line

        for x in range(0, width, pixel_step):
            base = x * channels
            if ctype == 3:
                index = line[base] * 3
                if index + 2 >= len(plte):
                    continue
                rgb = (plte[index], plte[index + 1], plte[index + 2])
            elif ctype in (0, 4):
                grey = line[base]
                rgb = (grey, grey, grey)
            else:
                rgb = (line[base], line[base + 1], line[base + 2])
            # Bucket to 5 bits per channel so near-identical pixels merge.
            key = (rgb[0] >> 3, rgb[1] >> 3, rgb[2] >> 3)
            counts[key] = counts.get(key, 0.0) + 1.0

    return [
        (((r << 3) / 255.0, (g << 3) / 255.0, (b << 3) / 255.0), weight)
        for (r, g, b), weight in counts.items()
    ]


def _unfilter_row(
    filter_type: int, line: bytearray, previous: bytearray, channels: int
) -> None:
    if filter_type == 0:
        return
    for i in range(len(line)):
        left = line[i - channels] if i >= channels else 0
        up = previous[i]
        up_left = previous[i - channels] if i >= channels else 0
        if filter_type == 1:
            line[i] = (line[i] + left) & 0xFF
        elif filter_type == 2:
            line[i] = (line[i] + up) & 0xFF
        elif filter_type == 3:
            line[i] = (line[i] + ((left + up) >> 1)) & 0xFF
        elif filter_type == 4:
            p = left + up - up_left
            pa, pb, pc = abs(p - left), abs(p - up), abs(p - up_left)
            pred = left if (pa <= pb and pa <= pc) else (up if pb <= pc else up_left)
            line[i] = (line[i] + pred) & 0xFF


def extract(path: str) -> list[Swatch]:
    """Swatches for an image, or an empty list when it cannot be read."""
    if not path or not os.path.isfile(path):
        return []
    swatches = _extract_imagemagick(path)
    if swatches:
        return swatches
    if path.lower().endswith(".png"):
        return _extract_png(path)
    return []


# ── Seed selection ─────────────────────────────────────────────────────


def pick_seed(swatches: list[Swatch]) -> color.RGB | None:
    """Choose the colour a human would call "the colour of this image".

    Frequency alone picks the sky or the background wash; chroma alone
    picks a three-pixel highlight. Scoring both, and penalising colours
    too close to black or white to survive as an accent, lands on the
    one that actually reads as the image's colour.
    """
    if not swatches:
        return None

    total = sum(weight for _, weight in swatches) or 1.0
    best: tuple[float, color.RGB] | None = None

    for rgb, weight in swatches:
        L, C, _ = color.rgb_to_oklch(rgb)
        share = weight / total

        # Chroma below this is grey; it cannot carry an accent.
        if C < 0.02:
            continue
        # Very dark or very light swatches make poor accents even when
        # they dominate the image.
        if L < 0.12 or L > 0.94:
            continue

        # share**0.35 keeps a large area meaningful without letting it
        # dominate; the lightness term prefers mid-tones.
        midtone = 1.0 - abs(L - 0.58) * 1.35
        score = (C ** 0.85) * (share ** 0.35) * max(midtone, 0.12)

        if best is None or score > best[0]:
            best = (score, rgb)

    if best is not None:
        return best[1]

    # Entirely grey wallpaper: fall back to the most common swatch so the
    # neutral ramp at least matches the image.
    return max(swatches, key=lambda item: item[1])[0]


def derive(
    wallpaper: str | None,
    fallback_accent: str = "#0A84FF",
    *,
    use_wallpaper: bool = True,
) -> Palette:
    """Build a palette, preferring the wallpaper and degrading cleanly."""
    fallback = color.parse_hex(fallback_accent)

    swatches: list[Swatch] = []
    if use_wallpaper and wallpaper:
        swatches = extract(wallpaper)

    seed = pick_seed(swatches) if swatches else None
    source = "wallpaper" if seed is not None else "fallback"
    if seed is None:
        seed = fallback

    L, C, h = color.rgb_to_oklch(seed)
    if source == "wallpaper":
        # A swatch lifted out of a photograph can be any lightness or
        # chroma; an accent has to survive on both light and dark glass,
        # so clamp it into a usable band. A colour the user chose by hand
        # is left exactly as they chose it.
        accent = color.oklch_to_rgb((
            min(max(L, 0.52), 0.74),
            min(max(C, 0.09), 0.19),
            h,
        ))
    else:
        accent = seed

    secondary = color.oklch_to_rgb((
        min(max(L, 0.55), 0.76), min(max(C * 0.7, 0.06), 0.14), (h + 38.0) % 360.0
    ))
    tertiary = color.oklch_to_rgb((
        min(max(L, 0.55), 0.78), min(max(C * 0.6, 0.05), 0.12), (h - 52.0) % 360.0
    ))
    # The neutral keeps a trace of the accent hue so greys feel related
    # to the wallpaper instead of sitting on top of it.
    neutral = color.oklch_to_rgb((L, min(C * 0.08, 0.016), h))

    top = sorted(swatches, key=lambda item: item[1], reverse=True)[:8]

    return Palette(
        seed=seed,
        accent=accent,
        secondary=secondary,
        tertiary=tertiary,
        neutral=neutral,
        source=source,
        swatches=[color.to_hex(rgb) for rgb, _ in top],
    )


def write_cache(palette: Palette, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(palette.as_dict(), handle, indent=2)
        handle.write("\n")
