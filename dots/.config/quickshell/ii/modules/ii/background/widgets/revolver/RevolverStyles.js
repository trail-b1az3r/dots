.pragma library

// The revolver's look for each Halcyon theme, and the outlines it is drawn with.
//
// Everything is laid out on the drum's 230 × 230 stage, centre (115, 115). The outlines are SVG path strings for
// QtQuick.Shapes' PathSvg, built here so the shapes are exact and the same everywhere they are used.

var CENTRE = 115;

// drum: the plate behind the chambers. chamber: each chamber's outline. orbit: chamber centres' distance from the
// middle. names: whether the chambers carry the game's name (small chambers only show the live one, below).
var STYLES = {
    "default": { id: "default", drum: "cookie", chamber: "circle", chamberSize: 50, orbit: 80, names: true,
                 hub: "dial", hammer: "block", glow: 0.35, waves: 8, statusLabel: true },
    "red-sun": { id: "red-sun", drum: "ring", chamber: "bead", chamberSize: 22, orbit: 92, names: false,
                 hub: "void", hammer: "notch", glow: 1.0, waves: 0, statusLabel: true },
    "glass":   { id: "glass", drum: "facets", chamber: "gem", chamberSize: 50, orbit: 80, names: true,
                 hub: "prism", hammer: "shard", glow: 0.5, waves: 0, statusLabel: true },
    "hyperneo": { id: "hyperneo", drum: "squircle", chamber: "squircle", chamberSize: 48, orbit: 79, names: true,
                  hub: "squircle", hammer: "pill", glow: 0.45, waves: 0, statusLabel: true },
    // The anime themes: squircles, drawn as keycaps (outline, a cream ring, a flat fill, a hard shadow straight down).
    "keycap":  { id: "keycap", drum: "squircle", plate: "keycap", chamber: "squircle", chamberSize: 48, orbit: 79, names: true,
                 hub: "squircle", hammer: "pill", glow: 0.45, waves: 0, statusLabel: true },
    "hsr":     { id: "hsr", drum: "rail", chamber: "star", chamberSize: 52, orbit: 80, names: true,
                 hub: "sparkle", hammer: "sparkle", glow: 0.6, waves: 0, statusLabel: true },
    // After ICEY, the revolver only: the game's cyan HUD over the dark navy of its wallpaper. A targeting reticle
    // (a fine tick ring, a scanning arc that runs as it turns, corner brackets, gold markers), hexagonal ice cells
    // for chambers, a snowflake hub and a chevron for the hammer.
    "icey":    { id: "icey", drum: "hud", chamber: "hex", chamberSize: 48, orbit: 80, names: true,
                 hub: "crystal", hammer: "chevron", glow: 0.75, waves: 0, statusLabel: true },
    // Manga Ink, the revolver only: drawn like a page of its wallpaper. A paper disc in a brush-stroke ensō with
    // screentone shading, speech-bubble chambers that point at a blush-pink heart, an ink-drop hammer, and speed
    // lines round it while it spins. Black ink and paper whatever the palette; the pink is the theme's accent.
    "ink":     { id: "ink", drum: "enso", chamber: "bubble", chamberSize: 56, orbit: 80, names: true,
                 hub: "heart", hammer: "drop", glow: 0.6, waves: 0, statusLabel: true, ink: "#141414", paper: "#f7f3ea" }
};

function styleFor(themeId) {
    switch (themeId) {
    case "red-sun":
    case "wallpaper-heaven-kenami":
        return STYLES["red-sun"];
    case "shattered-glass":
    case "fractured-glass":
        return STYLES["glass"];
    case "hyperneo":
        return STYLES["hyperneo"];
    case "after-icey":
    case "manga-ink":
        return STYLES["keycap"];
    case "hsr":
        return STYLES["hsr"];
    default:
        return STYLES["default"];
    }
}

// The revolver's own look: the theme's (styleFor), except where a theme has a revolver of its own.
function revolverStyleFor(themeId) {
    switch (themeId) {
    case "after-icey":
        return STYLES["icey"];
    case "manga-ink":
        return STYLES["ink"];
    default:
        return styleFor(themeId);
    }
}

// The four brackets of a targeting frame round a square of half-side h, each arm len long.
function brackets(cx, cy, h, len) {
    var d = "";
    var corners = [[-1, -1], [1, -1], [1, 1], [-1, 1]];
    for (var i = 0; i < 4; i++) {
        var sx = corners[i][0], sy = corners[i][1];
        var x = cx + sx * h, y = cy + sy * h;
        d += "M " + f(x - sx * len) + " " + f(y) + " L " + f(x) + " " + f(y) + " L " + f(x) + " " + f(y - sy * len) + " ";
    }
    return d;
}

// A small diamond, for the reticle's markers.
function diamond(cx, cy, r) {
    return closedPoly([[cx, cy - r], [cx + r * 0.7, cy], [cx, cy + r], [cx - r * 0.7, cy]]);
}

// A snowflake's six arms, each with two small branches, as one path of strokes.
function snowflake(cx, cy, r) {
    var d = "";
    for (var i = 0; i < 6; i++) {
        var t = (i * 60 - 90) * Math.PI / 180;
        var ex = cx + r * Math.cos(t), ey = cy + r * Math.sin(t);
        d += "M " + f(cx) + " " + f(cy) + " L " + f(ex) + " " + f(ey) + " ";
        var bx = cx + r * 0.6 * Math.cos(t), by = cy + r * 0.6 * Math.sin(t);
        for (var s = -1; s <= 1; s += 2) {
            var u = t + s * 0.75;
            d += "M " + f(bx) + " " + f(by) + " L " + f(bx + r * 0.3 * Math.cos(u)) + " " + f(by + r * 0.3 * Math.sin(u)) + " ";
        }
    }
    return d;
}

// The frame the dock, the top bar and the side panels take in a theme (dock/DockFrame.qml); "" keeps the plain
// panel (no theme, and the glass themes).
var FRAMES = { "hyperneo": "hyperneo", "hsr": "hsr", "red-sun": "red-sun", "wallpaper-heaven-kenami": "red-sun",
               "after-icey": "icey", "manga-ink": "ink" };

function frameKindFor(themeId) {
    return FRAMES[themeId] || "";
}

// A speech bubble of radius r round (cx, cy), its tail pointing along `tail` degrees (0 is right, 90 down).
function bubble(cx, cy, r, tail) {
    var t = tail * Math.PI / 180, spread = 0.3;
    var x1 = cx + r * Math.cos(t + spread), y1 = cy + r * Math.sin(t + spread);
    var x2 = cx + r * Math.cos(t - spread), y2 = cy + r * Math.sin(t - spread);
    var tip = r * 1.42;
    return "M " + f(x1) + " " + f(y1) + " A " + f(r) + " " + f(r) + " 0 1 1 " + f(x2) + " " + f(y2)
        + " L " + f(cx + tip * Math.cos(t)) + " " + f(cy + tip * Math.sin(t)) + " Z";
}

// A heart of half-width s round (cx, cy).
function heart(cx, cy, s) {
    return "M " + f(cx) + " " + f(cy + s * 0.95)
        + " C " + f(cx - s * 1.25) + " " + f(cy + s * 0.15) + " " + f(cx - s * 1.05) + " " + f(cy - s * 0.95) + " " + f(cx) + " " + f(cy - s * 0.35)
        + " C " + f(cx + s * 1.05) + " " + f(cy - s * 0.95) + " " + f(cx + s * 1.25) + " " + f(cy + s * 0.15) + " " + f(cx) + " " + f(cy + s * 0.95) + " Z";
}

// Screentone: a halftone of dots inside a circle of radius r, growing towards the lower right, as one path.
function screentone(cx, cy, r, step) {
    var d = "";
    for (var y = cy - r; y <= cy + r; y += step) {
        var row = Math.round((y - cy + r) / step);
        for (var x = cx - r + (row % 2) * step / 2; x <= cx + r; x += step) {
            var dx = x - cx, dy = y - cy;
            if (dx * dx + dy * dy > (r - 3) * (r - 3))
                continue;
            // How far into the shaded crescent: nothing towards the upper left, most at the lower-right rim.
            var shade = (Math.hypot(x - (cx - r * 0.35), y - (cy - r * 0.35)) - r * 0.95) / (r * 0.5);
            if (shade <= 0)
                continue;
            var dot = Math.min(1, shade) * step * 0.34;
            if (dot < 0.35)
                continue;
            d += "M " + f(x - dot) + " " + f(y) + " A " + f(dot) + " " + f(dot) + " 0 1 0 " + f(x + dot) + " " + f(y)
                + " A " + f(dot) + " " + f(dot) + " 0 1 0 " + f(x - dot) + " " + f(y) + " ";
        }
    }
    return d;
}

// How the wallpaper widgets draw their insides in each theme: the gauges, the spectrum's bars, progress lines,
// the current line of the lyrics and the labels. Colours left empty come from the theme's palette.
//
//   gauge     ring (a plain ring), glow (a thin lit ring with its light round it), segments (a ring of lit facets),
//             activity (three rings inside each other, one card), rail (a gold ring with star ticks),
//             key (a keycap that fills from the bottom)
//   bars      round, needle (thin lines with a lit tip), shard (sharp bars with a bright edge), pill,
//             star (bars topped with a four-point star), blocks (stacked squares, like a console's equaliser)
//   progress  line, glow, segments, pill, rail (a thin line with a diamond on it), blocks
//   lyric     plain, glow, frost, bold, rail (the line between two stars), key (the line on a keycap)
var LOOKS = {
    "default":  { id: "default", gauge: "ring", bars: "round", progress: "line", lyric: "plain",
                  caps: false, spacing: 0, colorA: "", colorB: "", text: "", glow: "" },
    "red-sun":  { id: "red-sun", gauge: "glow", bars: "needle", progress: "glow", lyric: "glow",
                  caps: true, spacing: 1.5, colorA: "#ff4940", colorB: "#ff9a6a", text: "#ffe2d6", glow: "#ff4940" },
    "glass":    { id: "glass", gauge: "segments", bars: "shard", progress: "segments", lyric: "frost",
                  caps: false, spacing: 0.5, colorA: "#e8f4ff", colorB: "#9fc4ff", text: "#ffffff", glow: "#bfe0ff" },
    "hyperneo": { id: "hyperneo", gauge: "activity", bars: "pill", progress: "pill", lyric: "bold",
                  caps: false, spacing: -0.2, colorA: "", colorB: "", text: "", glow: "" },
    "hsr":      { id: "hsr", gauge: "rail", bars: "star", progress: "rail", lyric: "rail",
                  caps: true, spacing: 2.2, colorA: "", colorB: "", text: "", glow: "" },
    "keycap":   { id: "keycap", gauge: "key", bars: "blocks", progress: "blocks", lyric: "key",
                  caps: true, spacing: 0.8, colorA: "", colorB: "", text: "", glow: "" }
};

function lookFor(themeId) {
    return LOOKS[styleFor(themeId).id] || LOOKS["default"];
}

function f(n) {
    return (Math.round(n * 100) / 100).toString();
}

function closedPoly(points) {
    var d = "M " + f(points[0][0]) + " " + f(points[0][1]);
    for (var i = 1; i < points.length; i++)
        d += " L " + f(points[i][0]) + " " + f(points[i][1]);
    return d + " Z";
}

// A circle as two arcs.
function circle(cx, cy, r) {
    return "M " + f(cx - r) + " " + f(cy) + " A " + f(r) + " " + f(r) + " 0 1 0 " + f(cx + r) + " " + f(cy)
         + " A " + f(r) + " " + f(r) + " 0 1 0 " + f(cx - r) + " " + f(cy) + " Z";
}

// An arc from a0 to a1 degrees (0 = right, clockwise on screen), not closed: for strokes.
function arc(cx, cy, r, a0, a1) {
    var t0 = a0 * Math.PI / 180, t1 = a1 * Math.PI / 180;
    var large = Math.abs(a1 - a0) > 180 ? 1 : 0;
    var sweep = a1 > a0 ? 1 : 0;
    return "M " + f(cx + r * Math.cos(t0)) + " " + f(cy + r * Math.sin(t0))
         + " A " + f(r) + " " + f(r) + " 0 " + large + " " + sweep + " " + f(cx + r * Math.cos(t1)) + " " + f(cy + r * Math.sin(t1));
}

// A wavy disc, like Material's cookie shapes: r·(1 + depth·cos(waves·θ)).
function cookie(cx, cy, r, waves, depth) {
    var pts = [];
    var n = 180;
    for (var i = 0; i < n; i++) {
        var t = i / n * Math.PI * 2;
        var rr = r * (1 + depth * Math.cos(waves * t));
        pts.push([cx + rr * Math.cos(t), cy + rr * Math.sin(t)]);
    }
    return closedPoly(pts);
}

// A superellipse |x|^k + |y|^k = r^k: Apple's squircle at k ≈ 4.5.
function squircle(cx, cy, r, k) {
    k = k || 4.5;
    var pts = [];
    var n = 120;
    for (var i = 0; i < n; i++) {
        var t = i / n * Math.PI * 2;
        var c = Math.cos(t), s = Math.sin(t);
        var x = r * Math.sign(c) * Math.pow(Math.abs(c), 2 / k);
        var y = r * Math.sign(s) * Math.pow(Math.abs(s), 2 / k);
        pts.push([cx + x, cy + y]);
    }
    return closedPoly(pts);
}

// A regular polygon with n sides, the first vertex at rot degrees.
function polygon(cx, cy, r, n, rot) {
    var pts = [];
    for (var i = 0; i < n; i++) {
        var t = (rot + i * 360 / n) * Math.PI / 180;
        pts.push([cx + r * Math.cos(t), cy + r * Math.sin(t)]);
    }
    return closedPoly(pts);
}

// A star with n points.
function star(cx, cy, rOut, rIn, n, rot) {
    var pts = [];
    for (var i = 0; i < n * 2; i++) {
        var r = i % 2 === 0 ? rOut : rIn;
        var t = (rot + i * 180 / n) * Math.PI / 180;
        pts.push([cx + r * Math.cos(t), cy + r * Math.sin(t)]);
    }
    return closedPoly(pts);
}

// A four-pointed sparkle with curved sides, the Star Rail mark.
function sparkle(cx, cy, r) {
    var p = [];
    var tips = [[0, -1], [1, 0], [0, 1], [-1, 0]];
    var d = "M " + f(cx) + " " + f(cy - r);
    for (var i = 0; i < 4; i++) {
        var a = tips[i], b = tips[(i + 1) % 4];
        // Control point pulled in towards the middle makes the concave sides.
        var mx = cx + (a[0] + b[0]) * r * 0.16, my = cy + (a[1] + b[1]) * r * 0.16;
        d += " Q " + f(mx) + " " + f(my) + " " + f(cx + b[0] * r) + " " + f(cy + b[1] * r);
    }
    return d + " Z";
}

// One of the triangles a faceted (glass) disc is cut into: centre, then two rim vertices.
function facet(cx, cy, r, n, i, rot) {
    var t0 = (rot + i * 360 / n) * Math.PI / 180, t1 = (rot + (i + 1) * 360 / n) * Math.PI / 180;
    return closedPoly([[cx, cy], [cx + r * Math.cos(t0), cy + r * Math.sin(t0)], [cx + r * Math.cos(t1), cy + r * Math.sin(t1)]]);
}

// A cut gem for a glass chamber: an octagon with its top face.
function gem(cx, cy, r) {
    return polygon(cx, cy, r, 8, 22.5);
}

function gemTable(cx, cy, r) {
    return polygon(cx, cy, r * 0.56, 8, 22.5);
}

// The tick marks of a dial, as one path of short strokes.
function ticks(cx, cy, r0, r1, n, rot) {
    var d = "";
    for (var i = 0; i < n; i++) {
        var t = (rot + i * 360 / n) * Math.PI / 180;
        d += "M " + f(cx + r0 * Math.cos(t)) + " " + f(cy + r0 * Math.sin(t)) + " L " + f(cx + r1 * Math.cos(t)) + " " + f(cy + r1 * Math.sin(t)) + " ";
    }
    return d;
}

// The two lit arcs of the Red Sun ring, broken where the painted ring is broken (measured from the wallpaper:
// a wide gap at the upper right and a narrow one at the upper left).
var RING_ARCS = [[-150, -42], [-8, 196]];

// Where the ring is painted in the Red Sun wallpaper, as fractions of the image: centre, and radius of its width.
var SUN_RING = { u: 0.4907, v: 0.4312, r: 0.0369 };

// The stage radius the lit ring is drawn at, to scale the drum onto the painted ring.
var SUN_RING_STAGE_RADIUS = 92;

// Chamber position on the stage, for chamber i of n.
function chamberPoint(i, n, orbit) {
    var t = i * (2 * Math.PI / n);
    return { x: CENTRE + Math.cos(t) * orbit, y: CENTRE + Math.sin(t) * orbit };
}

// ── Cards and plates for the other wallpaper widgets (ThemedPlate.qml) ──────────────────────────────────

// A superellipse stretched to rx × ry.
function squircleRect(cx, cy, rx, ry, k) {
    k = k || 5;
    var pts = [];
    var n = 160;
    for (var i = 0; i < n; i++) {
        var t = i / n * Math.PI * 2;
        var c = Math.cos(t), s = Math.sin(t);
        pts.push([cx + rx * Math.sign(c) * Math.pow(Math.abs(c), 2 / k), cy + ry * Math.sign(s) * Math.pow(Math.abs(s), 2 / k)]);
    }
    return closedPoly(pts);
}

// A rectangle with its corners cut off at 45°, like a cut stone.
function chamferRect(x, y, w, h, c) {
    return closedPoly([[x + c, y], [x + w - c, y], [x + w, y + c], [x + w, y + h - c], [x + w - c, y + h],
                       [x + c, y + h], [x, y + h - c], [x, y + c]]);
}

// A rectangle with round corners of radius r.
function roundRect(x, y, w, h, r) {
    r = Math.min(r, w / 2, h / 2);
    return "M " + f(x + r) + " " + f(y) + " L " + f(x + w - r) + " " + f(y)
         + " A " + f(r) + " " + f(r) + " 0 0 1 " + f(x + w) + " " + f(y + r)
         + " L " + f(x + w) + " " + f(y + h - r)
         + " A " + f(r) + " " + f(r) + " 0 0 1 " + f(x + w - r) + " " + f(y + h)
         + " L " + f(x + r) + " " + f(y + h)
         + " A " + f(r) + " " + f(r) + " 0 0 1 " + f(x) + " " + f(y + h - r)
         + " L " + f(x) + " " + f(y + r)
         + " A " + f(r) + " " + f(r) + " 0 0 1 " + f(x + r) + " " + f(y) + " Z";
}

// The outline of a plate of a given kind ("disc" or "card") in a style, inside w × h with an inset.
function plateOutline(style, kind, w, h, inset) {
    var cx = w / 2, cy = h / 2, rx = w / 2 - inset, ry = h / 2 - inset;
    if (kind === "disc") {
        switch (style.drum) {
        case "facets": return polygon(cx, cy, Math.min(rx, ry), 8, 22.5);
        case "squircle": return squircle(cx, cy, Math.min(rx, ry), 4.6);
        case "cookie": return cookie(cx, cy, Math.min(rx, ry) * 0.95, style.waves || 8, 0.04);
        default: return circle(cx, cy, Math.min(rx, ry));
        }
    }
    switch (style.drum) {
    case "facets": return chamferRect(inset, inset, w - 2 * inset, h - 2 * inset, Math.min(w, h) * 0.18);
    case "squircle": return squircleRect(cx, cy, rx, ry, 5);
    case "rail": return roundRect(inset, inset, w - 2 * inset, h - 2 * inset, 10);
    default: return roundRect(inset, inset, w - 2 * inset, h - 2 * inset, Math.min(w, h) / 2);
    }
}
