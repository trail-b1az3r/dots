#!/usr/bin/env python3
"""Build the Halcyon Glass cursor theme, in both XCursor and hyprcursor form.

Every shape is drawn here, from primitives: nothing is taken from another
cursor theme. The look matches the glass themes: a dark glass body with a
white outline, a blue-to-lavender glint along the inside of the rim, and a
soft shadow.

    pip install cairosvg pillow
    ./scripts/make-cursors.py            # writes the theme into the repo
    ./scripts/make-cursors.py --out DIR  # somewhere else
    ./scripts/make-cursors.py --preview preview.png

Output (committed, so installing needs none of this):
    dots/.local/share/icons/Halcyon-Glass/
        index.theme                 XCursor theme description
        cursors/                    XCursor files, plus symlinks for aliases
        manifest.hl                 hyprcursor theme description
        hyprcursors/*.hlc           hyprcursor shapes (zips of meta.hl + PNGs)
"""

import argparse
import io
import math
import os
import shutil
import struct
import zipfile
from pathlib import Path

import cairosvg
from PIL import Image, ImageChops, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
THEME = "Halcyon-Glass"
DEFAULT_OUT = ROOT / "dots/.local/share/icons" / THEME
SIZES = [24, 32, 48, 64, 96]
FRAMES = 10          # frames in the animated shapes
FRAME_MS = 60
CANVAS = 256         # SVG drawing units

# ---------------------------------------------------------------------------
# Drawing. A shape is a list of primitives that are drawn as one piece:
# first all their outlines, then all their fills over those, so where
# primitives overlap they merge without seams. "Details" are drawn on top.
# ---------------------------------------------------------------------------

STYLE = """
<defs>
  <linearGradient id="body" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#2A3048"/>
    <stop offset="1" stop-color="#0F121C"/>
  </linearGradient>
  <linearGradient id="glint" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#B4D2FF"/>
    <stop offset="1" stop-color="#D6BFFF"/>
  </linearGradient>
</defs>
"""
OUTLINE = 15   # white stroke, half of which shows outside the fill
GLINT = 5      # inner rim glint width, half of which shows inside


def rrect(x, y, w, h, r=None, rotate=None):
    r = min(w, h) / 2 if r is None else r
    t = f' transform="rotate({rotate[0]} {rotate[1]} {rotate[2]})"' if rotate else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}"{t}/>'


def poly(*points, rotate=None):
    t = f' transform="rotate({rotate} 128 128)"' if rotate else ""
    return f'<polygon points="{" ".join(f"{x},{y}" for x, y in points)}"{t}/>'


def circle(cx, cy, r):
    return f'<circle cx="{cx}" cy="{cy}" r="{r}"/>'


def ring(cx, cy, r_out, r_in):
    return (f'<path fill-rule="evenodd" d="M{cx - r_out},{cy} a{r_out},{r_out} 0 1,0 {2 * r_out},0 '
            f'a{r_out},{r_out} 0 1,0 {-2 * r_out},0 Z M{cx - r_in},{cy} a{r_in},{r_in} 0 1,0 {2 * r_in},0 '
            f'a{r_in},{r_in} 0 1,0 {-2 * r_in},0 Z"/>')


def svg(parts, details=""):
    """The shape and its details, as (picture, silhouette) SVGs.

    The glint along the inside of the rim is added when rasterising, from
    the silhouette: stroking each primitive would also light up the seams
    where primitives overlap inside the shape.
    """
    shapes = "".join(parts)
    head = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CANVAS} {CANVAS}" width="{CANVAS}" height="{CANVAS}">'
    picture = f"""{head}
{STYLE}
<g fill="#FFFFFF" stroke="#FFFFFF" stroke-width="{OUTLINE}" stroke-linejoin="round">{shapes}</g>
<g fill="url(#body)">{shapes}</g>
@GLINT@
{details}
</svg>"""
    silhouette = f'{head}<g fill="#FFFFFF">{shapes}</g></svg>'
    return picture, silhouette


def glyph(d, width=9):
    """White strokes drawn on top of a shape (question marks, plus signs...)."""
    return (f'<path d="{d}" fill="none" stroke="#FFFFFF" stroke-width="{width}" '
            'stroke-linecap="round" stroke-linejoin="round"/>')


def spinner_arc(cx, cy, r, frame, width=10):
    """A bright arc a quarter of the way round, rotated for the frame."""
    start = frame / FRAMES * 2 * math.pi
    end = start + math.pi * 0.6
    x1, y1 = cx + r * math.cos(start), cy + r * math.sin(start)
    x2, y2 = cx + r * math.cos(end), cy + r * math.sin(end)
    return (f'<path d="M{x1:.2f},{y1:.2f} A{r},{r} 0 0,1 {x2:.2f},{y2:.2f}" fill="none" '
            f'stroke="url(#glint)" stroke-width="{width}" stroke-linecap="round"/>')


ARROW = poly((44, 26), (44, 196), (86, 156), (114, 220), (146, 206), (118, 144), (176, 144))
BADGE = (190, 190, 40)   # small disc lower right, for help/copy/menu...


def with_badge(details):
    return [ARROW, circle(*BADGE)], details


def double_arrow(rotate=0, bar=False):
    shape = poly((128, 26), (178, 82), (146, 82), (146, 174), (178, 174), (128, 230),
                 (78, 174), (110, 174), (110, 82), (78, 82), rotate=rotate or None)
    parts = [shape]
    if bar:
        # A bar across the middle: the divider being dragged.
        parts.append(rrect(34, 116, 188, 24, 12, (rotate, 128, 128)))
    return parts


def hand_pointing():
    return [
        rrect(92, 22, 40, 126),                      # index finger
        rrect(70, 112, 130, 112, 38),                 # palm
        rrect(128, 94, 36, 72),                       # middle
        rrect(158, 104, 34, 66),                      # ring
        rrect(184, 118, 28, 58),                      # little
        rrect(42, 128, 40, 88, None, (-38, 62, 172)), # thumb
    ]


def hand_open():
    return [
        rrect(62, 112, 138, 112, 40),
        rrect(74, 44, 34, 100), rrect(110, 30, 36, 110), rrect(148, 38, 34, 104), rrect(182, 64, 30, 88),
        rrect(34, 124, 38, 84, None, (-40, 54, 166)),
    ]


def hand_closed():
    return [
        rrect(62, 104, 138, 116, 40),
        rrect(74, 84, 34, 56), rrect(108, 78, 36, 58), rrect(144, 80, 34, 56), rrect(176, 90, 30, 50),
        rrect(40, 124, 38, 70, None, (-60, 60, 160)),
    ]


def magnifier(sign):
    parts = [ring(110, 110, 70, 46), rrect(150, 150, 36, 90, None, (-45, 168, 195))]
    details = glyph("M88,110 L132,110" + (" M110,88 L110,132" if sign == "+" else ""), 12)
    return parts, details


# name: (parts, details, hotspot in drawing units, aliases); animated shapes
# give a function of the frame for their details.
def shapes():
    s = {}
    s["default"] = ([ARROW], "", (44, 26), [
        "left_ptr", "arrow", "top_left_arrow", "left_arrow"])
    s["pointer"] = (hand_pointing(), "", (112, 24), [
        "hand", "hand1", "hand2", "pointing_hand", "9d800788f1b08800ae810202380a0822",
        "e29285e634086352946a0e7090d73106"])
    s["text"] = ([rrect(118, 40, 20, 176, 10), rrect(86, 30, 84, 20, 10), rrect(86, 206, 84, 20, 10)],
                 "", (128, 128), ["xterm", "ibeam"])
    s["vertical-text"] = ([rrect(40, 118, 176, 20, 10), rrect(30, 86, 20, 84, 10), rrect(206, 86, 20, 84, 10)],
                          "", (128, 128), [])
    s["crosshair"] = ([rrect(118, 30, 20, 76, 10), rrect(118, 150, 20, 76, 10),
                       rrect(30, 118, 76, 20, 10), rrect(150, 118, 76, 20, 10), circle(128, 128, 10)],
                      "", (128, 128), ["cross", "tcross", "cross_reverse", "diamond_cross"])
    s["cell"] = ([rrect(108, 36, 40, 184, 12), rrect(36, 108, 184, 40, 12)], "", (128, 128), ["plus"])
    s["not-allowed"] = ([ring(128, 128, 88, 60), rrect(40, 114, 176, 28, 14, (45, 128, 128))], "", (128, 128), [
        "crossed_circle", "forbidden", "no-drop", "dnd-no-drop", "circle", "03b6e0fcb3499374a867c041f52298f0"])
    s["help"] = (*with_badge(glyph("M176,178 q0,-16 14,-16 q15,0 15,14 q0,10 -13,15 l0,7") +
                             '<circle cx="192" cy="214" r="5.5" fill="#FFFFFF"/>'), (44, 26), [
        "question_arrow", "whats_this", "left_ptr_help", "dnd-ask",
        "5c6cd98b3f3ebcb1f9c7f1c204630408", "d9ce0ab605698f320427677b458ad60b"])
    s["copy"] = (*with_badge(glyph("M174,190 L206,190 M190,174 L190,206", 10)), (44, 26), [
        "dnd-copy", "1081e37283d90000800003c07f3ef6bf", "6407b0e94181790501fd1e167b474872",
        "b66166c04f8c3109214a4fbd64a50fc8"])
    s["alias"] = (*with_badge(glyph("M176,204 L204,176 M184,176 L204,176 L204,196", 9)), (44, 26), [
        "link", "dnd-link", "3085a0e285430894940527032f8b26df", "640fb0e74195791501fd1ebd6ce7ea6d",
        "a2a266d0498c3104214a47bd64ab0fc8"])
    s["context-menu"] = (*with_badge(glyph("M174,178 L206,178 M174,190 L206,190 M174,202 L206,202", 7)),
                         (44, 26), [])
    s["grab"] = (hand_open(), "", (128, 128), ["openhand", "fleur_open", "5aca4d189052212118709018842178c0"])
    s["grabbing"] = (hand_closed(), "", (128, 128), [
        "closedhand", "dnd-move", "dnd-none", "move_grab", "208530c400c041818281048008011002",
        "fcf21c00b30f7e3f83fe0dfd12e71cff"])
    s["all-scroll"] = (double_arrow() + double_arrow(90), "", (128, 128), [
        "move", "fleur", "size_all", "4498f0e0c1937ffe01fd06f973665830", "9081237383d90e509aa00f00170e968f"])
    s["ns-resize"] = (double_arrow(), "", (128, 128), [
        "n-resize", "s-resize", "sb_v_double_arrow", "size_ver", "v_double_arrow", "top_side",
        "bottom_side", "00008160000006810000408080010102"])
    s["ew-resize"] = (double_arrow(90), "", (128, 128), [
        "e-resize", "w-resize", "sb_h_double_arrow", "size_hor", "h_double_arrow", "left_side",
        "right_side", "028006030e0e7ebffc7f7070c0600140"])
    s["nwse-resize"] = (double_arrow(-45), "", (128, 128), [
        "nw-resize", "se-resize", "size_fdiag", "top_left_corner", "bottom_right_corner",
        "bd_double_arrow", "c7088f0f3e6c8088236ef8e1e3e70000"])
    s["nesw-resize"] = (double_arrow(45), "", (128, 128), [
        "ne-resize", "sw-resize", "size_bdiag", "top_right_corner", "bottom_left_corner",
        "fd_double_arrow", "fcf1c3c07f7f3c0f8f3fc6f8c0f6b090"])
    s["col-resize"] = (double_arrow(90, bar=True), "", (128, 128), [
        "split_h", "14fef782d02440884392942c11205230"])
    s["row-resize"] = (double_arrow(0, bar=True), "", (128, 128), [
        "split_v", "2870a09082c103050810ffdffffe0204"])
    s["zoom-in"] = (*magnifier("+"), (110, 110), ["zoom_in"])
    s["zoom-out"] = (*magnifier("-"), (110, 110), ["zoom_out"])
    s["wait"] = ([circle(128, 128, 76)], lambda f: spinner_arc(128, 128, 52, f, 14), (128, 128), ["watch"])
    s["progress"] = ([ARROW, circle(190, 190, 42)], lambda f: spinner_arc(190, 190, 26, f, 9), (44, 26), [
        "left_ptr_watch", "half-busy", "08e8e1c95fe2fc01f976f1e063a24ccd", "3ecb610c1bf2410f44200f48c40d3599"])
    return s


# ---------------------------------------------------------------------------
# Rasterising
# ---------------------------------------------------------------------------

def rasterise(text, size):
    png = cairosvg.svg2png(bytestring=text.encode(), output_width=size, output_height=size)
    return Image.open(io.BytesIO(png)).convert("RGBA")


def render(svgs, size):
    """Render at size px: the shape, a glint inside its rim, a soft shadow."""
    picture, silhouette = svgs
    # Details (glyphs, spinner arcs) go over the glint, so render in two
    # passes: the body alone, then the details alone.
    body_svg, details_svg = picture.split("@GLINT@")
    shape = rasterise(body_svg + "</svg>", size)
    details = rasterise(body_svg.split("<g fill=")[0] + details_svg, size)

    # Glint: the silhouette minus a copy shrunk by the rim width.
    mask = rasterise(silhouette, size).getchannel("A")
    rim = max(1, round(size * GLINT / CANVAS / 2))
    inner = mask
    for _ in range(rim):
        inner = inner.filter(ImageFilter.MinFilter(3))
    edge = ImageChops.subtract(mask, inner).point(lambda a: a * 0.9)
    gradient = Image.linear_gradient("L").rotate(45, expand=False).resize((size, size))
    glint = Image.merge("RGB", [
        gradient.point(lambda g: 0xB4 + (0xD6 - 0xB4) * g // 255),
        gradient.point(lambda g: 0xD2 + (0xBF - 0xD2) * g // 255),
        gradient.point(lambda g: 0xFF),
    ]).convert("RGBA")
    glint.putalpha(edge)
    shape = Image.alpha_composite(shape, glint)
    shape = Image.alpha_composite(shape, details)
    alpha = shape.getchannel("A")
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    shadow.putalpha(alpha.point(lambda a: a * 0.45))
    offset = max(1, round(size / 32))
    shadow = shadow.transform(shadow.size, Image.AFFINE, (1, 0, 0, 0, 1, -offset))
    shadow = shadow.filter(ImageFilter.GaussianBlur(max(0.6, size / 40)))
    return Image.alpha_composite(shadow, shape)


def frames_of(shape):
    parts, details, hotspot, aliases = shape
    if callable(details):
        return [svg(parts, details(f)) for f in range(FRAMES)]
    return [svg(parts, details)]


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------

def xcursor_file(images):
    """images: list of (size, (xhot, yhot), delay_ms, PIL RGBA image)."""
    header_len, toc_len, chunk_header = 16, 12, 36
    positions, offset = [], header_len + toc_len * len(images)
    for size, _, _, _ in images:
        positions.append(offset)
        offset += chunk_header + size * size * 4
    out = bytearray(struct.pack("<4sIII", b"Xcur", header_len, 0x10000, len(images)))
    for (size, _, _, _), position in zip(images, positions):
        out += struct.pack("<III", 0xFFFD0002, size, position)
    for size, (xhot, yhot), delay, image in images:
        out += struct.pack("<IIIIIIIII", chunk_header, 0xFFFD0002, size, 1, size, size, xhot, yhot, delay)
        # XCursor wants premultiplied ARGB, little-endian 32-bit words (B, G, R, A in memory).
        raw = image.tobytes()
        data = bytearray(len(raw))
        for i in range(0, len(raw), 4):
            pr, pg, pb, pa = raw[i], raw[i + 1], raw[i + 2], raw[i + 3]
            data[i:i + 4] = bytes((pb * pa // 255, pg * pa // 255, pr * pa // 255, pa))
        out += data
    return bytes(out)


def build(out):
    if out.exists():
        shutil.rmtree(out)
    cursors = out / "cursors"
    hyprcursors = out / "hyprcursors"
    cursors.mkdir(parents=True)
    hyprcursors.mkdir()

    (out / "index.theme").write_text(
        f"[Icon Theme]\nName={THEME}\nComment=Halcyon's glass cursors, made for this desktop\nInherits=Adwaita\n")
    (out / "manifest.hl").write_text(
        f"name = {THEME}\ndescription = Halcyon's glass cursors, made for this desktop\n"
        "version = 1.0\ncursors_directory = hyprcursors\n")

    all_shapes = shapes()
    for name, shape in all_shapes.items():
        _, details, (hx, hy), aliases = shape
        svgs = frames_of(shape)
        animated = len(svgs) > 1
        delay = FRAME_MS if animated else 0

        xcursor_images = []
        meta = [
            "resize_algorithm = bilinear",
            f"hotspot_x = {hx / CANVAS:.4f}",
            f"hotspot_y = {hy / CANVAS:.4f}",
        ]
        meta += [f"define_override = {alias}" for alias in aliases]
        with zipfile.ZipFile(hyprcursors / f"{name}.hlc", "w", zipfile.ZIP_DEFLATED) as hlc:
            pngs = []
            for size in SIZES:
                hot = (round(size * hx / CANVAS), round(size * hy / CANVAS))
                for index, text in enumerate(svgs):
                    image = render(text, size)
                    xcursor_images.append((size, hot, delay, image))
                    filename = f"{size}-{index:02d}.png" if animated else f"{size}.png"
                    buffer = io.BytesIO()
                    image.save(buffer, "PNG", optimize=True)
                    pngs.append((filename, buffer.getvalue()))
                    meta.append(f"define_size = {size}, {filename}" + (f", {FRAME_MS}" if animated else ""))
            # Fixed timestamps, so rebuilding produces identical files.
            def entry(filename):
                info = zipfile.ZipInfo(filename, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                return info
            hlc.writestr(entry("meta.hl"), "\n".join(meta) + "\n")
            for filename, data in pngs:
                hlc.writestr(entry(filename), data)

        (cursors / name).write_bytes(xcursor_file(xcursor_images))
        for alias in aliases:
            link = cursors / alias
            if not link.exists():
                os.symlink(name, link)
    return all_shapes


def preview(path, all_shapes):
    size, pad, cols = 64, 16, 8
    names = list(all_shapes)
    rows = math.ceil(len(names) / cols)
    sheet = Image.new("RGBA", (cols * (size + pad) + pad, rows * (size + pad) + pad), (72, 84, 120, 255))
    for i, name in enumerate(names):
        image = render(frames_of(all_shapes[name])[0], size)
        x, y = pad + (i % cols) * (size + pad), pad + (i // cols) * (size + pad)
        sheet.alpha_composite(image, (x, y))
    sheet.save(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--preview", type=Path)
    args = parser.parse_args()
    all_shapes = build(args.out)
    if args.preview:
        preview(args.preview, all_shapes)
    count = sum(1 for _ in (args.out / "cursors").iterdir())
    print(f"wrote {args.out}: {len(all_shapes)} shapes, {count} cursor names")


if __name__ == "__main__":
    main()
