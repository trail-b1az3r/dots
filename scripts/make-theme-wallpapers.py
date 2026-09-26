#!/usr/bin/env python3
"""Draw the wallpapers for the Star Rail, Shattered Glass and Fractured Glass themes.

Both are procedural and original: nothing here is taken from a game or
any other artwork. Output is deterministic for a given seed, so running
this again reproduces the shipped files byte for byte on the same
Pillow/numpy versions.

    pip install pillow numpy
    ./scripts/make-theme-wallpapers.py            # writes into the themes dir
    ./scripts/make-theme-wallpapers.py --out DIR  # somewhere else

The HyperNeo theme uses the default wallpaper, so it has nothing here.
"""

import argparse
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 2560, 1440
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "dots/.config/hypr/hyprland/halcyon/themes/wallpapers"


def hex_rgb(value):
    value = value.lstrip("#")
    return np.array([int(value[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)


def smooth_noise(rng, scale, octaves=4):
    """Fractal value noise in [0, 1], built from blurred random fields."""
    total = np.zeros((H, W), dtype=np.float32)
    weight_sum = 0.0
    for octave in range(octaves):
        cells = max(2, int(scale * (2 ** octave)))
        small = rng.random((cells * H // W + 2, cells + 2)).astype(np.float32)
        img = Image.fromarray((small * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)
        weight = 0.5 ** octave
        total += np.asarray(img, dtype=np.float32) / 255.0 * weight
        weight_sum += weight
    total /= weight_sum
    return (total - total.min()) / (np.ptp(total) + 1e-6)


def to_image(rgb):
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")


# --------------------------------------------------------------------------
# Star Rail: a nebula, a star field, and a golden rail curving through it.
# --------------------------------------------------------------------------

def star_rail(seed=7):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    u, v = xx / W, yy / H

    # Base: deep navy at the top falling to indigo, with a violet bloom.
    top, bottom = hex_rgb("#070A1C"), hex_rgb("#130E2E")
    rgb = top[None, None] * (1 - v[..., None]) + bottom[None, None] * v[..., None]

    cloud = smooth_noise(rng, 3, 5)
    wisps = smooth_noise(rng, 7, 4)
    bloom = np.exp(-(((u - 0.68) / 0.32) ** 2 + ((v - 0.38) / 0.30) ** 2))
    nebula = np.clip(cloud * 1.35 - 0.45, 0, 1) * (0.35 + 0.65 * bloom)
    rgb += nebula[..., None] * hex_rgb("#6B4FC8")[None, None] * 0.55
    rgb += (np.clip(wisps - 0.55, 0, 1) * bloom)[..., None] * hex_rgb("#C7A6FF")[None, None] * 0.45
    # A warm glow where the rail meets the horizon.
    glow = np.exp(-(((u - 0.18) / 0.22) ** 2 + ((v - 0.78) / 0.12) ** 2))
    rgb += glow[..., None] * hex_rgb("#E0A95A")[None, None] * 0.35

    img = to_image(rgb)
    draw = ImageDraw.Draw(img, "RGBA")

    # Stars, denser inside the nebula.
    for _ in range(2600):
        x, y = rng.random() * W, rng.random() * H
        if rng.random() > 0.35 + 0.65 * bloom[int(y), int(x)]:
            continue
        r = rng.choice([0.6, 0.8, 1.0, 1.4, 2.0], p=[0.4, 0.3, 0.17, 0.09, 0.04])
        warm = rng.random() < 0.18
        colour = (255, 226, 170) if warm else (220, 228, 255)
        alpha = int(120 + rng.random() * 135)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=colour + (alpha,))

    # A few bright stars with a soft cross flare.
    flare = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fdraw = ImageDraw.Draw(flare)
    for _ in range(14):
        x, y = rng.random() * W, rng.random() * H * 0.75
        length = 18 + rng.random() * 34
        fdraw.line((x - length, y, x + length, y), fill=(255, 236, 200, 150), width=2)
        fdraw.line((x, y - length, x, y + length), fill=(255, 236, 200, 150), width=2)
        fdraw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(255, 248, 230, 255))
    img = Image.alpha_composite(img.convert("RGBA"), flare.filter(ImageFilter.GaussianBlur(1.2)))

    # A faint compass ring behind everything in the upper right.
    ring = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rdraw = ImageDraw.Draw(ring)
    cx, cy, rad = W * 0.70, H * 0.36, H * 0.30
    for k, (r, width, alpha) in enumerate([(rad, 3, 70), (rad * 0.93, 1, 50), (rad * 1.12, 1, 35)]):
        rdraw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(232, 196, 120, alpha), width=width)
    for tick in range(72):
        angle = tick / 72 * 2 * math.pi
        inner = rad * (0.95 if tick % 6 else 0.88)
        rdraw.line(
            (cx + inner * math.cos(angle), cy + inner * math.sin(angle),
             cx + rad * math.cos(angle), cy + rad * math.sin(angle)),
            fill=(232, 196, 120, 80 if tick % 6 == 0 else 45), width=2 if tick % 6 == 0 else 1)
    img = Image.alpha_composite(img, ring.filter(ImageFilter.GaussianBlur(0.6)))

    # The rail: two parallel curves sweeping out of the lower left, with
    # sleepers, drawn on a glow layer and then sharp on top.
    def rail_point(t, offset):
        # A cubic Bezier from the lower-left corner up into the nebula.
        p0, p1, p2, p3 = (-0.05, 1.08), (0.30, 0.86), (0.52, 0.52), (0.95, 0.20)
        x = ((1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * p1[0]
             + 3 * (1 - t) * t ** 2 * p2[0] + t ** 3 * p3[0])
        y = ((1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * p1[1]
             + 3 * (1 - t) * t ** 2 * p2[1] + t ** 3 * p3[1])
        # Tangent, for the perpendicular offset between the two rails.
        dx = (3 * (1 - t) ** 2 * (p1[0] - p0[0]) + 6 * (1 - t) * t * (p2[0] - p1[0])
              + 3 * t ** 2 * (p3[0] - p2[0]))
        dy = (3 * (1 - t) ** 2 * (p1[1] - p0[1]) + 6 * (1 - t) * t * (p2[1] - p1[1])
              + 3 * t ** 2 * (p3[1] - p2[1]))
        norm = math.hypot(dx * W, dy * H) or 1
        width = (1 - t) ** 1.6 * 70 + 4  # perspective: narrower as it recedes
        return (x * W - dy * H / norm * width * offset, y * H + dx * W / norm * width * offset)

    steps = [i / 400 for i in range(401)]
    glow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sharp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gdraw, sdraw = ImageDraw.Draw(glow_layer), ImageDraw.Draw(sharp)
    for i in range(0, 400, 9):
        t = steps[i]
        a, b = rail_point(t, -1.25), rail_point(t, 1.25)
        alpha = int(150 * (1 - t) + 30)
        sdraw.line(a + b, fill=(150, 112, 70, alpha), width=max(1, int(5 * (1 - t))))
    for side in (-1, 1):
        pts = [rail_point(t, side) for t in steps]
        for j in range(len(pts) - 1):
            t = steps[j]
            width = max(1, int(7 * (1 - t) ** 1.2))
            gdraw.line(pts[j] + pts[j + 1], fill=(255, 196, 110, 200), width=width + 10)
            sdraw.line(pts[j] + pts[j + 1], fill=(255, 226, 160, 255), width=width)
    img = Image.alpha_composite(img, glow_layer.filter(ImageFilter.GaussianBlur(14)))
    img = Image.alpha_composite(img, sharp)
    return img.convert("RGB")


# --------------------------------------------------------------------------
# Shattered Glass: a pane broken from one impact point, each shard
# refracting the light behind it a little differently.
# --------------------------------------------------------------------------

def shattered_glass(seed=11):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    impact = np.array([W * 0.63, H * 0.44], dtype=np.float32)

    # Real breaks run two ways: radial cracks out from the impact, and
    # concentric cracks crossing them. A shard is one cell of that web, so
    # label every pixel by (ring, sector) in polar coordinates.
    dx, dy = (xx - impact[0]) / 1.2, yy - impact[1]
    theta = np.mod(np.arctan2(dy, dx), 2 * math.pi)
    radius = np.hypot(dx, dy)

    sectors = 26
    angles = np.sort(np.linspace(0, 2 * math.pi, sectors, endpoint=False)
                     + rng.normal(0, 0.09, sectors)) % (2 * math.pi)
    angles.sort()
    rings = 13
    ring_base = 16 * 1.47 ** np.arange(rings)
    # Radius of each concentric crack where it meets each radial crack.
    # Interpolating between neighbours makes the rings straight-sided.
    ring_at = ring_base[:, None] * (1 + rng.normal(0, 0.16, (rings, sectors)))

    sector = np.searchsorted(angles, theta) % sectors
    prev_angle = angles[(sector - 1) % sectors]
    span = np.mod(angles[sector] - prev_angle, 2 * math.pi) + 1e-6
    frac = np.mod(theta - prev_angle, 2 * math.pi) / span
    ring = np.zeros((H, W), dtype=np.int32)
    for j in range(rings):
        boundary = ring_at[j][(sector - 1) % sectors] * (1 - frac) + ring_at[j][sector] * frac
        ring += (radius > boundary).astype(np.int32)

    # Radial cracks kink where they cross a ring, and not all of them
    # make it to the edge of the pane: far out, neighbours merge.
    kinked = (angles[None, :] + rng.normal(0, 0.035, (rings + 1, sectors))) % (2 * math.pi)
    kinked.sort(axis=1)
    sector = np.empty((H, W), dtype=np.int32)
    for j in range(rings + 1):
        mask = ring == j
        sector[mask] = np.searchsorted(kinked[j], theta[mask]) % sectors
    merge = np.arange(sectors)
    for j in range(rings + 1):
        if j >= 7:
            for k in range(0, sectors, 2):
                if rng.random() < 0.45:
                    merge[k] = merge[(k + 1) % sectors]
        mask = ring == j
        sector[mask] = merge[sector[mask]]
    label = ring * sectors + sector
    n = (rings + 1) * sectors

    # The light behind the glass: a cool gradient with a pale window glow.
    u, v = xx / W, yy / H

    def backlight(du, dv):
        uu, vv = u + du, v + dv
        base = (hex_rgb("#081019")[None, None] * (1 - vv[..., None])
                + hex_rgb("#0E2230")[None, None] * vv[..., None])
        glow = np.exp(-(((uu - 0.62) / 0.35) ** 2 + ((vv - 0.40) / 0.30) ** 2))
        base = base + glow[..., None] * hex_rgb("#3D7FA6")[None, None] * 0.75
        haze = np.exp(-(((uu - 0.25) / 0.25) ** 2 + ((vv - 0.75) / 0.25) ** 2))
        return base + haze[..., None] * hex_rgb("#5B4A9E")[None, None] * 0.45

    # Each shard samples the backlight at its own offset and brightness,
    # which is what makes them read as separate pieces of glass.
    shift_u = rng.normal(0, 0.035, n).astype(np.float32)
    shift_v = rng.normal(0, 0.035, n).astype(np.float32)
    gain = (0.78 + rng.random(n) * 0.45).astype(np.float32)
    rgb = backlight(shift_u[label], shift_v[label]) * gain[label][..., None]

    # A sheen across each shard, at a per-shard angle.
    angle = rng.random(n).astype(np.float32) * math.pi
    along = (xx * np.cos(angle[label]) + yy * np.sin(angle[label])) / W
    sheen = np.clip(np.sin(along * 9 + rng.random(n)[label] * 6) * 0.5 + 0.5, 0, 1) ** 6
    rgb += sheen[..., None] * np.array([160, 210, 255], dtype=np.float32)[None, None] * 0.22

    # Prismatic edges on a few shards: split the tint into warm/cool fringes.
    prism = rng.random(n) < 0.08
    fringe = prism[label].astype(np.float32) * sheen
    rgb[..., 0] += fringe * 70
    rgb[..., 2] += np.roll(fringe, 6, axis=1) * 90

    # Cracks: wherever the shard changes, plus a bright halo at the impact.
    edge = np.zeros((H, W), dtype=bool)
    edge[:, 1:] |= label[:, 1:] != label[:, :-1]
    edge[1:, :] |= label[1:, :] != label[:-1, :]
    crack = Image.fromarray((edge * 255).astype(np.uint8))
    crack_glow = np.asarray(crack.filter(ImageFilter.GaussianBlur(3)), dtype=np.float32) / 255
    crack_core = np.asarray(crack.filter(ImageFilter.GaussianBlur(0.7)), dtype=np.float32) / 255
    dist = np.hypot(xx - impact[0], yy - impact[1])
    near = np.exp(-dist / 700)
    rgb += crack_glow[..., None] * np.array([120, 200, 255], dtype=np.float32) * (0.5 + near)[..., None]
    rgb += crack_core[..., None] * np.array([235, 248, 255], dtype=np.float32) * (0.35 + 0.65 * near)[..., None]
    halo = np.exp(-dist / 90)
    rgb += halo[..., None] * np.array([200, 235, 255], dtype=np.float32) * 0.9

    # Fine grain so large flat shards don't band.
    rgb += rng.normal(0, 2.2, (H, W, 1)).astype(np.float32)
    return to_image(rgb)


# --------------------------------------------------------------------------
# Fractured Glass: a few large, calm fragments of thick glass over a soft,
# vivid backdrop, each refracting it by its own amount, with dispersion
# along the fracture lines. No impact point, nothing violent.
# --------------------------------------------------------------------------

def fractured_glass(seed=23):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    u, v = xx / W, yy / H

    # The backdrop: soft blobs of colour on deep indigo.
    base = hex_rgb("#0B0C1A")[None, None] * np.ones((H, W, 1), dtype=np.float32)
    blobs = [((0.22, 0.30), 0.30, "#3A6BFF"), ((0.70, 0.22), 0.28, "#9B5CFF"),
             ((0.82, 0.78), 0.30, "#FF6FB1"), ((0.30, 0.82), 0.26, "#2FD3C8"),
             ((0.52, 0.52), 0.22, "#5B7CFF")]
    backdrop = base.copy()
    for (cx, cy), radius, colour in blobs:
        falloff = np.exp(-(((u - cx) / radius) ** 2 + ((v - cy) / (radius * 1.1)) ** 2))
        backdrop += falloff[..., None] * hex_rgb(colour)[None, None] * 0.75
    backdrop = np.clip(backdrop, 0, 255)

    # Fragments: a sparse Voronoi, so there are only a dozen or so pieces.
    points = np.column_stack([rng.random(16) * W, rng.random(16) * H]).astype(np.float32)
    label = np.empty((H, W), dtype=np.int32)
    for y0 in range(0, H, 120):
        sub_x, sub_y = xx[y0:y0 + 120], yy[y0:y0 + 120]
        d = (sub_x[..., None] - points[:, 0]) ** 2 + (sub_y[..., None] - points[:, 1]) ** 2
        label[y0:y0 + 120] = np.argmin(d, axis=-1)
    n = len(points)

    # Each fragment is a slightly different thickness: it shifts and
    # magnifies what is behind it around its own centre.
    counts = np.bincount(label.ravel(), minlength=n).astype(np.float32) + 1
    cx = np.bincount(label.ravel(), weights=xx.ravel(), minlength=n) / counts
    cy = np.bincount(label.ravel(), weights=yy.ravel(), minlength=n) / counts
    shift = rng.normal(0, 38, (n, 2)).astype(np.float32)
    zoom = (1.0 + rng.random(n) * 0.10).astype(np.float32)
    sx = cx[label] + (xx - cx[label]) / zoom[label] + shift[label, 0]
    sy = cy[label] + (yy - cy[label]) / zoom[label] + shift[label, 1]
    sx = np.clip(sx, 0, W - 1).astype(np.int32)
    sy = np.clip(sy, 0, H - 1).astype(np.int32)
    rgb = backdrop[sy, sx]

    # A soft sheen across each fragment, like light on a glass face.
    angle = rng.random(n).astype(np.float32) * math.pi
    along = ((xx - cx[label]) * np.cos(angle[label]) + (yy - cy[label]) * np.sin(angle[label])) / 900
    rgb += (np.clip(1 - np.abs(along - 0.1) * 3, 0, 1) ** 3)[..., None] * 28
    rgb *= (0.92 + rng.random(n) * 0.14).astype(np.float32)[label][..., None]

    # Fracture lines, with dispersion: red and blue fringes either side.
    edge = np.zeros((H, W), dtype=bool)
    edge[:, 1:] |= label[:, 1:] != label[:, :-1]
    edge[1:, :] |= label[1:, :] != label[:-1, :]
    line = Image.fromarray((edge * 255).astype(np.uint8))
    core = np.asarray(line.filter(ImageFilter.GaussianBlur(0.8)), dtype=np.float32) / 255
    glow = np.asarray(line.filter(ImageFilter.GaussianBlur(4)), dtype=np.float32) / 255
    rgb += core[..., None] * 170 + glow[..., None] * 45
    rgb[..., 0] += np.roll(glow, 3, axis=1) * 60
    rgb[..., 2] += np.roll(glow, -3, axis=1) * 70

    rgb += rng.normal(0, 1.8, (H, W, 1)).astype(np.float32)
    return to_image(rgb)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for name, draw in (("star-rail.jpg", star_rail), ("shattered-glass.jpg", shattered_glass),
                       ("fractured-glass.jpg", fractured_glass)):
        path = args.out / name
        draw().save(path, quality=92, optimize=True, progressive=True)
        print(f"wrote {path} ({path.stat().st_size // 1024} KiB)")


if __name__ == "__main__":
    main()
