"""Generate Halcyon's shipped wallpapers.

Deliberately not gradients-with-noise. Each one is built from a small
number of large, soft forms so that palette extraction finds a real
accent — a wallpaper whose colours are all near-grey produces a dull
desktop, and one with a dozen competing hues produces an unstable one.

Written as PNG with zlib, no dependencies.
"""
from __future__ import annotations

import math
import os
import struct
import zlib

W, H = 2560, 1440

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "assets", "wallpapers")


def srgb(c: float) -> int:
    c = 0.0 if c < 0 else 1.0 if c > 1 else c
    v = 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055
    return max(0, min(255, int(round(v * 255))))


def lin(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_lin(value: str) -> tuple[float, float, float]:
    value = value.lstrip("#")
    return tuple(lin(int(value[i:i + 2], 16) / 255.0) for i in (0, 2, 4))  # type: ignore[return-value]


def smoothstep(edge0: float, edge1: float, x: float) -> float:
    if edge1 == edge0:
        return 0.0
    t = (x - edge0) / (edge1 - edge0)
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    return t * t * (3 - 2 * t)


def write_png(path: str, rows: list[bytearray]) -> None:
    raw = bytearray()
    for row in rows:
        raw.append(0)
        raw += row
    compressed = zlib.compress(bytes(raw), 9)

    def chunk(tag: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + tag
            + payload
            + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
        )

    with open(path, "wb") as handle:
        handle.write(b"\x89PNG\r\n\x1a\n")
        handle.write(chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)))
        handle.write(chunk(b"IDAT", compressed))
        handle.write(chunk(b"IEND", b""))


def render(name: str, base: str, forms: list[dict], vignette: float = 0.35) -> None:
    """Composite soft radial forms in linear light over a base colour."""
    br, bg, bb = hex_lin(base)
    prepared = [
        (
            f["x"] * W, f["y"] * H, f["r"] * W,
            *hex_lin(f["color"]), f.get("strength", 1.0), f.get("falloff", 2.0),
        )
        for f in forms
    ]
    rows: list[bytearray] = []
    for y in range(H):
        row = bytearray()
        ny = y / H
        for x in range(W):
            r, g, b = br, bg, bb
            for fx, fy, fr, cr, cg, cb, strength, falloff in prepared:
                dx, dy = x - fx, y - fy
                distance = math.sqrt(dx * dx + dy * dy)
                if distance >= fr:
                    continue
                a = (1.0 - distance / fr) ** falloff * strength
                r += (cr - r) * a
                g += (cg - g) * a
                b += (cb - b) * a
            if vignette:
                nx = x / W
                edge = smoothstep(0.35, 1.0, math.hypot(nx - 0.5, ny - 0.5) * 1.45)
                shade = 1.0 - edge * vignette
                r, g, b = r * shade, g * shade, b * shade
            row += bytes((srgb(r), srgb(g), srgb(b)))
        rows.append(row)
    path = os.path.join(OUT, name)
    write_png(path, rows)
    print("wrote", path)


os.makedirs(OUT, exist_ok=True)

render(
    "halcyon-dusk.png",
    base="#070a12",
    forms=[
        {"x": 0.24, "y": 0.30, "r": 0.62, "color": "#1d4ed8", "strength": 0.85},
        {"x": 0.72, "y": 0.22, "r": 0.48, "color": "#6d4aff", "strength": 0.55},
        {"x": 0.58, "y": 0.86, "r": 0.70, "color": "#0b2a4a", "strength": 0.80, "falloff": 1.6},
        {"x": 0.12, "y": 0.92, "r": 0.34, "color": "#00b4c8", "strength": 0.30},
    ],
)

render(
    "halcyon-dawn.png",
    base="#f2ede6",
    forms=[
        {"x": 0.30, "y": 0.26, "r": 0.60, "color": "#ffb27a", "strength": 0.70},
        {"x": 0.78, "y": 0.34, "r": 0.50, "color": "#8fb8e8", "strength": 0.60},
        {"x": 0.50, "y": 0.90, "r": 0.66, "color": "#e6d2c0", "strength": 0.75, "falloff": 1.6},
        {"x": 0.90, "y": 0.86, "r": 0.30, "color": "#c9a2d8", "strength": 0.35},
    ],
    vignette=0.12,
)

render(
    "halcyon-slate.png",
    base="#0c0e11",
    forms=[
        {"x": 0.50, "y": 0.44, "r": 0.78, "color": "#1b2330", "strength": 0.90, "falloff": 1.5},
        {"x": 0.22, "y": 0.70, "r": 0.42, "color": "#2f7d6b", "strength": 0.45},
        {"x": 0.80, "y": 0.28, "r": 0.38, "color": "#3a4a63", "strength": 0.50},
    ],
    vignette=0.28,
)
