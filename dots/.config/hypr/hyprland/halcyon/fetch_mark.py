"""The Halcyon mark as a solid, drawn in characters and turned in 3D.

Used by `halcyon-theme fetch`. Pure Python, no dependencies.

The mark is the same sword and trident as `assets/icons/halcyon.svg`, but
described here as flat outlines that are extruded into thin solids. Each
solid is triangulated, rotated about a vertical axis, projected with a
little perspective, and rasterised into a character grid with a depth
buffer. Brightness comes from a single light, mapped onto a density ramp.

Everything is pure: no terminal, no clock. `fetch` decides when to draw a
frame and how long to wait between them; this module only answers "what
does the mark look like at this angle".
"""

from __future__ import annotations

import math
from typing import Sequence

Point = tuple[float, float]
Vec3 = tuple[float, float, float]
Triangle = tuple[Vec3, Vec3, Vec3, Vec3]  # three corners and a face normal

# Outlines, in the 256 × 256 space of the SVG mark. Each is (points, half
# thickness in normalised units). The points are the same shapes the SVG
# draws: the sword is on the left, the trident on the right.
_RECT_BLADE_GUARD = [(62, 186), (138, 186), (138, 199), (62, 199)]
_GRIP = [(91, 199), (109, 199), (109, 233), (91, 233)]
_SHAFT = [(151, 78), (161, 78), (161, 242), (151, 242)]
_COLLAR = [(132, 104), (180, 104), (180, 115), (132, 115)]
_BLADE = [(100, 18), (112, 62), (112, 186), (100, 200), (88, 186), (88, 62)]
_FORK = [
    (156, 10), (163, 36), (176, 22), (172, 50), (168, 50), (168, 96),
    (144, 96), (144, 50), (140, 50), (136, 22), (149, 36),
]


def _circle(cx: float, cy: float, r: float, n: int = 12) -> list[Point]:
    return [
        (cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n))
        for i in range(n)
    ]


#: Every solid in the mark: (outline in 256 space, half thickness).
SOLIDS: tuple[tuple[Sequence[Point], float], ...] = (
    (_BLADE, 0.030),
    (_RECT_BLADE_GUARD, 0.045),
    (_GRIP, 0.040),
    (_circle(100, 242, 10), 0.050),
    (_SHAFT, 0.030),
    (_COLLAR, 0.045),
    (_FORK, 0.030),
)


# ── Triangulation ──────────────────────────────────────────────────────


def _cross(o: Point, a: Point, b: Point) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _inside(p: Point, a: Point, b: Point, c: Point) -> bool:
    return _cross(a, b, p) > 0 and _cross(b, c, p) > 0 and _cross(c, a, p) > 0


def triangulate(poly: Sequence[Point]) -> list[tuple[int, int, int]]:
    """Ear-clipping triangulation of a simple polygon, as index triples.

    The polygon may be concave, as the trident's fork is. Winding is
    normalised first, so callers need not care which way round it is drawn.
    """
    pts = list(poly)
    if len(pts) < 3:
        raise ValueError("a polygon needs at least three corners")
    area = sum(
        pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
        for i in range(len(pts))
    )
    order = list(range(len(pts)))
    if area < 0:
        order.reverse()
    remaining = order
    triangles: list[tuple[int, int, int]] = []
    while len(remaining) > 3:
        clipped = False
        for k in range(len(remaining)):
            i0 = remaining[k - 1]
            i1 = remaining[k]
            i2 = remaining[(k + 1) % len(remaining)]
            a, b, c = pts[i0], pts[i1], pts[i2]
            if _cross(a, b, c) <= 0:
                continue  # reflex corner: cannot be an ear
            others = (pts[j] for j in remaining if j not in (i0, i1, i2))
            if any(_inside(p, a, b, c) for p in others):
                continue
            triangles.append((i0, i1, i2))
            remaining = remaining[:k] + remaining[k + 1 :]
            clipped = True
            break
        if not clipped:
            raise ValueError("polygon is not simple; cannot triangulate it")
    if len(remaining) == 3:
        triangles.append(tuple(remaining))  # type: ignore[arg-type]
    return triangles


# ── The model ──────────────────────────────────────────────────────────


def _to_model(p: Point) -> tuple[float, float]:
    """256-space outline to normalised model units, origin at the centre."""
    return ((p[0] - 128.0) / 128.0, (128.0 - p[1]) / 128.0)


def _sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross3(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _unit(v: Vec3) -> Vec3:
    length = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2) or 1.0
    return (v[0] / length, v[1] / length, v[2] / length)


def _flat(a: Vec3, b: Vec3, c: Vec3) -> Vec3:
    return _unit(_cross3(_sub(b, a), _sub(c, a)))


def build_model() -> list[Triangle]:
    """Every triangle of the mark, with a flat normal for each one."""
    triangles: list[Triangle] = []
    for outline, half in SOLIDS:
        pts = [_to_model(p) for p in outline]
        # Winding is normalised inside triangulate(); the side walls need
        # the same orientation, so make it explicit here as well.
        if sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
               for i in range(len(pts))) < 0:
            pts.reverse()

        front = [(x, y, half) for x, y in pts]
        back = [(x, y, -half) for x, y in pts]
        for i0, i1, i2 in triangulate(pts):
            a, b, c = front[i0], front[i1], front[i2]
            triangles.append((a, b, c, (0.0, 0.0, 1.0)))
            a, b, c = back[i0], back[i1], back[i2]
            triangles.append((a, b, c, (0.0, 0.0, -1.0)))

        for i in range(len(pts)):
            j = (i + 1) % len(pts)
            dx, dy = pts[j][0] - pts[i][0], pts[j][1] - pts[i][1]
            length = math.hypot(dx, dy) or 1.0
            # For a counter-clockwise outline the outside is to the right
            # of each edge.
            normal = (dy / length, -dx / length, 0.0)
            a, b = front[i], front[j]
            c, d = back[j], back[i]
            triangles.append((a, b, c, normal))
            triangles.append((a, c, d, normal))
    return triangles


MODEL: list[Triangle] = build_model()


# ── Projection and rasterisation ───────────────────────────────────────

#: Distance from the eye to the origin, in model units. Smaller is more
#: perspective; larger is closer to a flat drawing.
CAMERA = 3.2

#: Light arriving from the upper left and in front of the mark.
LIGHT = _unit((-0.45, 0.65, 0.75))

#: Density ramp, darkest to brightest.
RAMP = " .:-=+*#%@"


def _rotate(v: Vec3, yaw: float, pitch: float) -> Vec3:
    x, y, z = v
    cy, sy = math.cos(yaw), math.sin(yaw)
    x, z = x * cy + z * sy, -x * sy + z * cy
    cp, sp = math.cos(pitch), math.sin(pitch)
    y, z = y * cp - z * sp, y * sp + z * cp
    return (x, y, z)


def _edge(a: Point, b: Point, p: Point) -> float:
    return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])


def render_frame(
    yaw: float,
    *,
    pitch: float = 0.22,
    cols: int = 34,
    rows: int = 18,
    fill: float = 0.92,
) -> list[str]:
    """The mark turned by `yaw` radians, as `rows` lines of `cols` characters.

    `pitch` tilts the mark a little towards the viewer so its top is seen
    from slightly above. Terminal cells are about twice as tall as they are
    wide, so the horizontal scale is twice the vertical one.
    """
    depth = [[-math.inf] * cols for _ in range(rows)]
    shade = [[0.0] * cols for _ in range(rows)]
    cells_per_unit_x = rows * fill
    cells_per_unit_y = rows / 2.0 * fill

    def project(v: Vec3) -> tuple[float, float, float]:
        x, y, z = _rotate(v, yaw, pitch)
        k = CAMERA / (CAMERA - z)
        col = cols / 2.0 + x * k * cells_per_unit_x
        row = rows / 2.0 - y * k * cells_per_unit_y
        return col, row, z

    for a, b, c, normal in MODEL:
        n = _rotate(normal, yaw, pitch)
        # Keep only the faces that point at the eye; a closed solid's back
        # faces are hidden anyway, so this only saves work.
        if n[2] <= -0.001:
            continue
        brightness = max(0.0, n[0] * LIGHT[0] + n[1] * LIGHT[1] + n[2] * LIGHT[2])
        level = 0.16 + 0.84 * brightness

        pa, pb, pc = project(a), project(b), project(c)
        p2 = [(pa[0], pa[1]), (pb[0], pb[1]), (pc[0], pc[1])]
        area = _edge(p2[0], p2[1], p2[2])
        if abs(area) < 1e-9:
            continue
        min_col = max(0, int(math.floor(min(q[0] for q in p2))))
        max_col = min(cols - 1, int(math.floor(max(q[0] for q in p2))))
        min_row = max(0, int(math.floor(min(q[1] for q in p2))))
        max_row = min(rows - 1, int(math.floor(max(q[1] for q in p2))))

        for row in range(min_row, max_row + 1):
            for col in range(min_col, max_col + 1):
                p = (col + 0.5, row + 0.5)
                w0 = _edge(p2[1], p2[2], p) / area
                w1 = _edge(p2[2], p2[0], p) / area
                w2 = _edge(p2[0], p2[1], p) / area
                if w0 < 0 or w1 < 0 or w2 < 0:
                    continue
                z = w0 * pa[2] + w1 * pb[2] + w2 * pc[2]
                if z > depth[row][col]:
                    depth[row][col] = z
                    shade[row][col] = level

    lines: list[str] = []
    for row in range(rows):
        chars = []
        for col in range(cols):
            if depth[row][col] == -math.inf:
                chars.append(" ")
            else:
                index = min(len(RAMP) - 1, int(shade[row][col] * (len(RAMP) - 1) + 0.5))
                chars.append(RAMP[index])
        lines.append("".join(chars).rstrip())
    # Trim whole empty columns on the left and right so the mark sits
    # snugly against the info beside it.
    width = max((len(line) for line in lines), default=0)
    lines = [line.ljust(width) for line in lines]
    left = min((len(line) - len(line.lstrip()) for line in lines if line.strip()), default=0)
    right = max((len(line.rstrip()) for line in lines), default=0)
    return [line[left:right] for line in lines]


def frame_width(frame: Sequence[str]) -> int:
    return max((len(line) for line in frame), default=0)
