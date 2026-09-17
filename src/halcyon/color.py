"""Colour maths for the Halcyon design system.

Tonal ramps and accent derivation run through OKLab rather than HSL.
HSL's "lightness" is not perceptual, so an HSL ramp produces steps that
look uneven and accents that shift hue as they darken — exactly the
tell-tale of a theme that was generated rather than designed. OKLab
costs a few more lines and removes the problem.

Everything here is pure functions over `(r, g, b)` floats in 0..1 plus
hex strings; no I/O, no state.
"""

from __future__ import annotations

import math
import re
from typing import Iterable

RGB = tuple[float, float, float]

_HEX_RE = re.compile(r"^#?([0-9a-fA-F]{3,8})$")


# ── Parsing and formatting ─────────────────────────────────────────────


def parse_hex(value: str) -> RGB:
    """Accept #rgb, #rgba, #rrggbb and #rrggbbaa; alpha is discarded."""
    match = _HEX_RE.match(value.strip())
    if not match:
        raise ValueError(f"Not a hex colour: {value!r}")
    digits = match.group(1)
    if len(digits) in (3, 4):
        digits = "".join(ch * 2 for ch in digits[:3])
    elif len(digits) in (6, 8):
        digits = digits[:6]
    else:
        raise ValueError(f"Not a hex colour: {value!r}")
    return (
        int(digits[0:2], 16) / 255.0,
        int(digits[2:4], 16) / 255.0,
        int(digits[4:6], 16) / 255.0,
    )


def to_hex(rgb: RGB) -> str:
    r, g, b = (_clamp01(c) for c in rgb)
    return "#{:02x}{:02x}{:02x}".format(
        round(r * 255), round(g * 255), round(b * 255)
    )


def to_rgba_css(rgb: RGB, alpha: float) -> str:
    r, g, b = (_clamp01(c) for c in rgb)
    return "rgba({}, {}, {}, {:.3f})".format(
        round(r * 255), round(g * 255), round(b * 255), _clamp01(alpha)
    )


def to_hypr(rgb: RGB, alpha: float = 1.0) -> str:
    """Hyprland accepts `rgba(RRGGBBAA)` as a string in Lua configs."""
    r, g, b = (_clamp01(c) for c in rgb)
    return "rgba({:02x}{:02x}{:02x}{:02x})".format(
        round(r * 255), round(g * 255), round(b * 255), round(_clamp01(alpha) * 255)
    )


def to_argb_hex(rgb: RGB, alpha: float = 1.0) -> str:
    """`#AARRGGBB`, which is what QML's Qt.rgba-free string form expects."""
    r, g, b = (_clamp01(c) for c in rgb)
    return "#{:02x}{:02x}{:02x}{:02x}".format(
        round(_clamp01(alpha) * 255), round(r * 255), round(g * 255), round(b * 255)
    )


def _clamp01(value: float) -> float:
    return 0.0 if value < 0.0 else 1.0 if value > 1.0 else value


# ── sRGB ↔ linear ↔ OKLab ──────────────────────────────────────────────


def _srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(c: float) -> float:
    if c <= 0.0031308:
        return 12.92 * c
    return 1.055 * (max(c, 0.0) ** (1 / 2.4)) - 0.055


def rgb_to_oklab(rgb: RGB) -> tuple[float, float, float]:
    r, g, b = (_srgb_to_linear(_clamp01(c)) for c in rgb)

    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b

    l_, m_, s_ = (_cbrt(l), _cbrt(m), _cbrt(s))
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def _oklab_to_linear(lab: tuple[float, float, float]) -> tuple[float, float, float]:
    """Linear sRGB, unclamped — values outside 0..1 are outside the gamut."""
    L, a, b = lab
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b

    l, m, s = l_**3, m_**3, s_**3

    return (
        +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    )


#: Rounding to 8 bits per channel forgives far more than this.
_GAMUT_EPSILON = 1e-5


def _in_gamut(linear: tuple[float, float, float]) -> bool:
    return all(-_GAMUT_EPSILON <= c <= 1.0 + _GAMUT_EPSILON for c in linear)


def oklab_to_rgb(lab: tuple[float, float, float]) -> RGB:
    """OKLab to sRGB, gamut-mapped by reducing chroma.

    Clipping each channel independently is the obvious thing to do and it
    is wrong: it moves the hue. A saturated blue pushed to a light
    lightness comes back visibly purple. Instead, when the colour falls
    outside sRGB, hold L and hue and binary-search the largest chroma that
    fits — which is what CSS Color 4 specifies, and what keeps a tonal
    ramp reading as one hue from end to end.
    """
    linear = _oklab_to_linear(lab)
    if _in_gamut(linear):
        return (
            _clamp01(_linear_to_srgb(linear[0])),
            _clamp01(_linear_to_srgb(linear[1])),
            _clamp01(_linear_to_srgb(linear[2])),
        )

    L, a, b = lab
    chroma_ = math.hypot(a, b)
    if chroma_ <= 0.0:
        # A grey already out of range: nothing to reduce, so clamp.
        return (
            _clamp01(_linear_to_srgb(linear[0])),
            _clamp01(_linear_to_srgb(linear[1])),
            _clamp01(_linear_to_srgb(linear[2])),
        )

    hue = math.atan2(b, a)
    cos_h, sin_h = math.cos(hue), math.sin(hue)
    low, high = 0.0, chroma_
    for _ in range(24):
        mid = (low + high) / 2.0
        if _in_gamut(_oklab_to_linear((L, mid * cos_h, mid * sin_h))):
            low = mid
        else:
            high = mid

    fitted = _oklab_to_linear((L, low * cos_h, low * sin_h))
    return (
        _clamp01(_linear_to_srgb(fitted[0])),
        _clamp01(_linear_to_srgb(fitted[1])),
        _clamp01(_linear_to_srgb(fitted[2])),
    )


def _cbrt(x: float) -> float:
    return math.copysign(abs(x) ** (1 / 3), x)


def rgb_to_oklch(rgb: RGB) -> tuple[float, float, float]:
    L, a, b = rgb_to_oklab(rgb)
    return (L, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360.0)


def oklch_to_rgb(lch: tuple[float, float, float]) -> RGB:
    L, C, h = lch
    rad = math.radians(h)
    return oklab_to_rgb((L, C * math.cos(rad), C * math.sin(rad)))


# ── Derivations ────────────────────────────────────────────────────────


def with_lightness(rgb: RGB, lightness: float) -> RGB:
    """Move a colour to a target OKLab lightness, keeping hue and chroma."""
    _, C, h = rgb_to_oklch(rgb)
    return oklch_to_rgb((_clamp01(lightness), C, h))


def with_chroma(rgb: RGB, chroma: float) -> RGB:
    L, _, h = rgb_to_oklch(rgb)
    return oklch_to_rgb((L, max(0.0, chroma), h))


def scale_chroma(rgb: RGB, factor: float) -> RGB:
    L, C, h = rgb_to_oklch(rgb)
    return oklch_to_rgb((L, max(0.0, C * factor), h))


def shift_hue(rgb: RGB, degrees: float) -> RGB:
    L, C, h = rgb_to_oklch(rgb)
    return oklch_to_rgb((L, C, (h + degrees) % 360.0))


def mix(a: RGB, b: RGB, t: float) -> RGB:
    """Perceptual mix. `t = 0` returns `a`, `t = 1` returns `b`."""
    t = _clamp01(t)
    la, aa, ba = rgb_to_oklab(a)
    lb, ab, bb = rgb_to_oklab(b)
    return oklab_to_rgb((
        la + (lb - la) * t,
        aa + (ab - aa) * t,
        ba + (bb - ba) * t,
    ))


def lightness(rgb: RGB) -> float:
    return rgb_to_oklch(rgb)[0]


def chroma(rgb: RGB) -> float:
    return rgb_to_oklch(rgb)[1]


def relative_luminance(rgb: RGB) -> float:
    """WCAG relative luminance, for contrast ratios."""
    r, g, b = (_srgb_to_linear(_clamp01(c)) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a: RGB, b: RGB) -> float:
    la, lb = relative_luminance(a), relative_luminance(b)
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


def readable_on(background: RGB, *, target: float = 4.5) -> RGB:
    """Pick black or white text for a background, then nudge it.

    Returns whichever pole has more contrast, pulled slightly toward the
    background when it already clears the target — pure #fff on a dark
    glass panel reads as harsh, and softening it is the difference
    between "themed" and "designed".
    """
    white: RGB = (1.0, 1.0, 1.0)
    black: RGB = (0.0, 0.0, 0.0)
    pole = white if contrast_ratio(white, background) >= contrast_ratio(black, background) else black

    for t in (0.14, 0.1, 0.06, 0.03, 0.0):
        candidate = mix(pole, background, t)
        if contrast_ratio(candidate, background) >= target:
            return candidate
    return pole


def ensure_contrast(foreground: RGB, background: RGB, target: float = 4.5) -> RGB:
    """Push a foreground colour until it clears a contrast target.

    Used for accent-coloured text, where we want to keep the accent's hue
    but refuse to ship something unreadable.
    """
    if contrast_ratio(foreground, background) >= target:
        return foreground

    bg_light = relative_luminance(background) > 0.35
    L, C, h = rgb_to_oklch(foreground)
    step = -0.04 if bg_light else 0.04
    for _ in range(24):
        L = _clamp01(L + step)
        candidate = oklch_to_rgb((L, C, h))
        if contrast_ratio(candidate, background) >= target:
            return candidate
        if L in (0.0, 1.0):
            break
    return readable_on(background, target=target)


def tonal_ramp(rgb: RGB, stops: Iterable[float]) -> dict[int, str]:
    """A Material-style tone ramp keyed by 0..100 lightness."""
    ramp: dict[int, str] = {}
    for stop in stops:
        ramp[int(round(stop))] = to_hex(with_lightness(rgb, stop / 100.0))
    return ramp
