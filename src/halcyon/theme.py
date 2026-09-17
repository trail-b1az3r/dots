"""Resolving settings into the design tokens every surface reads.

Waybar, Quickshell and Hyprland each want colours in a different format,
and each of them would happily drift out of sync with the other two if
they derived their own. So they do not: this module produces one token
document, and `halcyon.render` translates it into the three dialects.

The vocabulary is deliberately small — surface, border, highlight, text,
accent, elevation — because a design system with forty colour roles is a
design system nobody can hold in their head.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any

from . import color
from .palette import Palette

# ── Quality tiers ──────────────────────────────────────────────────────

#: Hyprland blur cost per quality tier. `size` is the sample distance and
#: `passes` the number of downsample/upsample rounds; both multiply GPU
#: cost, so the low tier halves both rather than only one.
BLUR_TIERS = {
    "off": {"enabled": False, "size": 1, "passes": 1, "newOptimizations": True, "xray": True},
    "low": {"enabled": True, "size": 4, "passes": 1, "newOptimizations": True, "xray": True},
    "medium": {"enabled": True, "size": 6, "passes": 2, "newOptimizations": True, "xray": True},
    "high": {"enabled": True, "size": 9, "passes": 3, "newOptimizations": True, "xray": False},
    "ultra": {"enabled": True, "size": 12, "passes": 4, "newOptimizations": True, "xray": False},
}

SHADOW_TIERS = {
    "off": {"enabled": False, "range": 0, "renderPower": 1},
    "low": {"enabled": True, "range": 8, "renderPower": 2},
    "medium": {"enabled": True, "range": 16, "renderPower": 3},
    "high": {"enabled": True, "range": 26, "renderPower": 3},
    "ultra": {"enabled": True, "range": 38, "renderPower": 4},
}

#: Base durations in milliseconds, before the preset and speed scale.
MOTION_PRESETS = {
    "minimal": {"scale": 0.55, "spring": False, "overshoot": 0.0},
    "macos": {"scale": 1.0, "spring": True, "overshoot": 0.06},
    "smooth": {"scale": 1.3, "spring": True, "overshoot": 0.1},
    "fast": {"scale": 0.7, "spring": False, "overshoot": 0.0},
    "disabled": {"scale": 0.0, "spring": False, "overshoot": 0.0},
}

BASE_DURATIONS = {
    "instant": 90,
    "quick": 160,
    "standard": 240,
    "emphasised": 380,
    "slow": 560,
    "overlay": 300,
    "workspace": 340,
    "hud": 200,
}

#: Cubic-bezier control points shared by QML and Hyprland so an overlay
#: fading in over a window matches the window's own motion.
CURVES = {
    # Control points are (x1, y1, x2, y2) of a cubic bezier. x must rise
    # monotonically from 0 to 1 or the curve folds back on itself and both
    # Hyprland and QML render it as a stutter.
    "standard": [0.4, 0.0, 0.2, 1.0],
    "decelerate": [0.0, 0.0, 0.2, 1.0],
    "accelerate": [0.4, 0.0, 1.0, 1.0],
    "emphasised": [0.2, 0.0, 0.0, 1.0],
    "gentle": [0.25, 0.1, 0.25, 1.0],
    # y may leave 0..1 — that is the overshoot.
    "overshoot": [0.34, 1.56, 0.64, 1.0],
    "linear": [0.0, 0.0, 1.0, 1.0],
}


def _clamp(value: float, low: float, high: float) -> float:
    return low if value < low else high if value > high else value


def _num(mapping: dict[str, Any], key: str, default: float) -> float:
    value = mapping.get(key, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ── Mode ───────────────────────────────────────────────────────────────


def resolve_mode(settings: dict[str, Any], palette: Palette) -> str:
    """Decide light or dark.

    `auto` follows the wallpaper: a bright wallpaper under dark chrome
    looks like a mistake, and vice versa. `followSunset` overrides that
    with the clock for people who want the day to change the desktop.
    """
    appearance = settings.get("appearance", {})
    mode = str(appearance.get("mode", "dark")).lower()

    if mode in ("light", "dark"):
        return mode

    if appearance.get("followSunset"):
        hour = _dt.datetime.now().hour
        return "light" if 7 <= hour < 19 else "dark"

    if palette.source == "wallpaper":
        return "light" if color.lightness(palette.seed) > 0.62 else "dark"
    return "dark"


# ── Token resolution ───────────────────────────────────────────────────


def resolve(settings: dict[str, Any], palette: Palette) -> dict[str, Any]:
    """Turn settings plus a palette into the full token document."""
    mode = resolve_mode(settings, palette)
    access = settings.get("accessibility", {})
    graphics = settings.get("graphics", {})
    glass_in = settings.get("glass", {})

    high_contrast = bool(access.get("highContrast"))
    disable_blur = bool(access.get("disableBlur"))
    low_power = bool(graphics.get("lowPowerGraphics"))

    glass = _resolve_glass(glass_in, access, graphics)
    colors = _resolve_colors(mode, palette, glass, high_contrast)
    motion = _resolve_motion(settings, access)
    typography = _resolve_typography(settings, access)

    blur_tier = "off" if disable_blur else str(graphics.get("blurQuality", "high"))
    if low_power and blur_tier not in ("off", "low"):
        blur_tier = "low"
    shadow_tier = str(graphics.get("shadowQuality", "high"))
    if low_power and shadow_tier not in ("off", "low"):
        shadow_tier = "low"

    blur = dict(BLUR_TIERS.get(blur_tier, BLUR_TIERS["high"]))
    blur["size"] = max(1, int(round(blur["size"] * glass["blurStrength"])))
    shadow = dict(SHADOW_TIERS.get(shadow_tier, SHADOW_TIERS["high"]))
    shadow["range"] = int(round(shadow["range"] * glass["shadowStrength"] * 1.4))

    radius = int(round(glass["cornerRadius"]))
    bar = settings.get("bar", {})

    return {
        "generated": _dt.datetime.now(_dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "mode": mode,
        "preset": glass_in.get("preset", "tinted"),
        "palette": palette.as_dict(),
        "color": colors,
        "glass": glass,
        "blur": blur,
        "shadow": shadow,
        "radius": {
            "xs": max(2, round(radius * 0.33)),
            "sm": max(4, round(radius * 0.55)),
            "md": max(6, round(radius * 0.78)),
            "lg": radius,
            "xl": round(radius * 1.45),
            "xxl": round(radius * 2.0),
            "window": radius,
            "full": 9999,
            # A continuous ("squircle") corner needs a higher power; 2.0
            # is a plain circular arc. Hyprland exposes this directly.
            "power": 3.0
            if settings.get("appearance", {}).get("cornerStyle") == "continuous"
            else 2.0,
        },
        "spacing": _spacing(glass),
        "typography": typography,
        "motion": motion,
        "elevation": _elevation(colors, glass),
        "bar": {
            "enabled": bool(bar.get("enabled", True)),
            "position": bar.get("position", "top"),
            "height": int(bar.get("height", 34)),
            "sideMargin": int(bar.get("sideMargin", 10)),
            "topMargin": int(bar.get("topMargin", 6)),
            "floating": bool(bar.get("floating", True)),
        },
        "quality": {
            "blur": blur_tier,
            "shadow": shadow_tier,
            "animation": "off"
            if motion["disabled"]
            else str(graphics.get("animationQuality", "high")),
            "lowPower": low_power,
        },
        "accessibility": {
            "highContrast": high_contrast,
            "reducedMotion": motion["reduced"],
            "disableBlur": disable_blur,
            "focusRing": bool(access.get("focusRing", True)),
            "screenReaderLabels": bool(access.get("screenReaderLabels", True)),
        },
    }


def _resolve_glass(
    glass_in: dict[str, Any], access: dict[str, Any], graphics: dict[str, Any]
) -> dict[str, float]:
    opacity = _num(glass_in, "opacity", 0.6)
    border = _num(glass_in, "borderOpacity", 0.34)
    blur_strength = _num(glass_in, "blurStrength", 1.0)
    saturation = _num(glass_in, "saturation", 1.2)
    tint = _num(glass_in, "tintStrength", 0.22)
    specular = _num(glass_in, "specularStrength", 0.5)
    refraction = _num(glass_in, "refraction", 0.4)
    noise = _num(glass_in, "noise", 0.012)

    # A global transparency dial, so a user can keep their preset and
    # still make everything more solid.
    transparency = _clamp(_num(graphics, "transparency", 1.0), 0.0, 1.0)
    opacity = 1.0 - (1.0 - opacity) * transparency

    # Accessibility floors win over the preset, always.
    floor = _clamp(_num(access, "minimumTransparency", 0.0), 0.0, 1.0)
    opacity = max(opacity, floor)

    if access.get("disableBlur"):
        # Without blur, a translucent panel is just an unreadable panel.
        opacity = max(opacity, 0.94)
        blur_strength = 0.0
        refraction = 0.0

    if access.get("highContrast"):
        opacity = max(opacity, 0.92)
        border = max(border, 0.8)
        tint = min(tint, 0.08)
        specular = min(specular, 0.2)
        noise = 0.0

    return {
        "opacity": round(_clamp(opacity, 0.05, 1.0), 4),
        "blurStrength": round(_clamp(blur_strength, 0.0, 2.0), 4),
        "saturation": round(_clamp(saturation, 0.5, 2.0), 4),
        "tintStrength": round(_clamp(tint, 0.0, 1.0), 4),
        "borderOpacity": round(_clamp(border, 0.0, 1.0), 4),
        "cornerRadius": _clamp(_num(glass_in, "cornerRadius", 18), 0, 48),
        "shadowStrength": round(_clamp(_num(glass_in, "shadowStrength", 0.55), 0.0, 1.5), 4),
        "panelPadding": _clamp(_num(glass_in, "panelPadding", 12), 0, 48),
        "widgetSpacing": _clamp(_num(glass_in, "widgetSpacing", 10), 0, 48),
        "specularStrength": round(_clamp(specular, 0.0, 1.0), 4),
        "refraction": round(_clamp(refraction, 0.0, 1.0), 4),
        "noise": round(_clamp(noise, 0.0, 0.1), 5),
        "elevationSpread": round(_clamp(_num(glass_in, "elevationSpread", 1.0), 0.2, 2.0), 4),
    }


def _resolve_colors(
    mode: str, palette: Palette, glass: dict[str, float], high_contrast: bool
) -> dict[str, str]:
    dark = mode == "dark"
    accent = palette.accent
    neutral = palette.neutral

    # Surfaces are built from the neutral, then tinted toward the accent
    # by tintStrength. That single knob is what separates "Ultra Clear"
    # from "Tinted" without needing two colour schemes.
    if dark:
        base = color.with_lightness(neutral, 0.16)
        raised = color.with_lightness(neutral, 0.22)
        sunken = color.with_lightness(neutral, 0.11)
        backdrop = color.with_lightness(neutral, 0.07)
        highlight = (1.0, 1.0, 1.0)
        border_base = (1.0, 1.0, 1.0)
        text_target = 7.0 if high_contrast else 5.2
    else:
        base = color.with_lightness(neutral, 0.95)
        raised = color.with_lightness(neutral, 0.985)
        sunken = color.with_lightness(neutral, 0.88)
        backdrop = color.with_lightness(neutral, 0.97)
        highlight = (1.0, 1.0, 1.0)
        border_base = (0.0, 0.0, 0.0)
        text_target = 7.0 if high_contrast else 5.0

    tint = glass["tintStrength"]
    surface = color.mix(base, accent, tint * 0.34)
    surface_raised = color.mix(raised, accent, tint * 0.28)
    surface_sunken = color.mix(sunken, accent, tint * 0.30)
    backdrop = color.mix(backdrop, accent, tint * 0.18)

    text = color.readable_on(surface, target=text_target)
    text_secondary = color.mix(text, surface, 0.32)
    text_tertiary = color.mix(text, surface, 0.52)
    text_disabled = color.mix(text, surface, 0.68)

    accent_text = color.ensure_contrast(accent, surface, 4.5 if not high_contrast else 7.0)
    on_accent = color.readable_on(accent, target=4.5)

    border_alpha = glass["borderOpacity"]
    specular = glass["specularStrength"]

    semantic = {
        "success": color.oklch_to_rgb((0.72 if dark else 0.58, 0.16, 148.0)),
        "warning": color.oklch_to_rgb((0.80 if dark else 0.68, 0.16, 78.0)),
        "danger": color.oklch_to_rgb((0.66 if dark else 0.56, 0.20, 25.0)),
        "info": accent,
    }

    tokens: dict[str, str] = {
        # Opaque roles — safe anywhere, including as a window background.
        "accent": color.to_argb_hex(accent),
        "accentText": color.to_argb_hex(accent_text),
        "accentHover": color.to_argb_hex(color.with_lightness(accent, color.lightness(accent) + (0.06 if dark else -0.05))),
        "accentPressed": color.to_argb_hex(color.with_lightness(accent, color.lightness(accent) - (0.06 if dark else -0.09))),
        "onAccent": color.to_argb_hex(on_accent),
        "secondary": color.to_argb_hex(palette.secondary),
        "tertiary": color.to_argb_hex(palette.tertiary),

        "text": color.to_argb_hex(text),
        "textSecondary": color.to_argb_hex(text_secondary),
        "textTertiary": color.to_argb_hex(text_tertiary),
        "textDisabled": color.to_argb_hex(text_disabled),

        "backdrop": color.to_argb_hex(backdrop),
        "surfaceSolid": color.to_argb_hex(surface),
        "surfaceRaisedSolid": color.to_argb_hex(surface_raised),

        # Glass roles — these carry the preset's alpha and are what the
        # shell actually paints with.
        "surface": color.to_argb_hex(surface, glass["opacity"]),
        "surfaceRaised": color.to_argb_hex(surface_raised, min(1.0, glass["opacity"] + 0.08)),
        "surfaceSunken": color.to_argb_hex(surface_sunken, max(0.0, glass["opacity"] - 0.1)),
        "surfaceHover": color.to_argb_hex(highlight if dark else (0.0, 0.0, 0.0), 0.07 * (1.4 if dark else 1.0)),
        "surfacePressed": color.to_argb_hex(highlight if dark else (0.0, 0.0, 0.0), 0.12 * (1.4 if dark else 1.0)),
        "surfaceSelected": color.to_argb_hex(accent, 0.20),

        "glassTint": color.to_argb_hex(accent, 0.10 + tint * 0.14),
        "glassHighlight": color.to_argb_hex(highlight, 0.10 + specular * 0.32),
        "glassSpecular": color.to_argb_hex(highlight, 0.04 + specular * 0.14),
        "glassBorder": color.to_argb_hex(border_base, border_alpha * (0.5 if dark else 0.14)),
        "glassBorderStrong": color.to_argb_hex(border_base, border_alpha * (0.85 if dark else 0.26)),
        "glassInnerShadow": color.to_argb_hex((0.0, 0.0, 0.0), 0.16 if dark else 0.06),

        "separator": color.to_argb_hex(border_base, border_alpha * (0.32 if dark else 0.12)),
        "shadow": color.to_argb_hex((0.0, 0.0, 0.0), 0.5 * glass["shadowStrength"] + 0.1),
        "scrim": color.to_argb_hex((0.0, 0.0, 0.0), 0.42 if dark else 0.28),

        "workspaceActive": color.to_argb_hex(accent),
        "workspaceOccupied": color.to_argb_hex(text_secondary, 0.75),
        "workspaceIdle": color.to_argb_hex(text_tertiary, 0.4),

        # Window chrome, used by Hyprland's border gradients.
        "borderActive": color.to_argb_hex(accent, 0.9),
        "borderActiveEnd": color.to_argb_hex(color.shift_hue(accent, 26.0), 0.75),
        "borderInactive": color.to_argb_hex(border_base, border_alpha * (0.34 if dark else 0.16)),
    }

    for name, rgb in semantic.items():
        tokens[name] = color.to_argb_hex(rgb)
        tokens[f"on{name.capitalize()}"] = color.to_argb_hex(color.readable_on(rgb))

    return tokens


def _spacing(glass: dict[str, float]) -> dict[str, int]:
    gap = int(round(glass["widgetSpacing"]))
    pad = int(round(glass["panelPadding"]))
    return {
        "xxs": max(2, round(gap * 0.2)),
        "xs": max(3, round(gap * 0.4)),
        "sm": max(4, round(gap * 0.6)),
        "md": gap,
        "lg": round(gap * 1.6),
        "xl": round(gap * 2.4),
        "panel": pad,
        "panelTight": max(4, round(pad * 0.6)),
        "panelLoose": round(pad * 1.5),
    }


def _resolve_typography(
    settings: dict[str, Any], access: dict[str, Any]
) -> dict[str, Any]:
    appearance = settings.get("appearance", {})
    scale = _num(appearance, "fontSizeScale", 1.0)
    scale *= _num(access, "textScale", 1.0)
    if access.get("largeText"):
        scale *= 1.18
    scale = _clamp(scale, 0.75, 2.0)

    def size(base: float) -> int:
        return max(8, int(round(base * scale)))

    return {
        "family": appearance.get("fontUi") or "Inter",
        "mono": appearance.get("fontMono") or "JetBrains Mono",
        "scale": round(scale, 4),
        "size": {
            "caption": size(11),
            "footnote": size(12),
            "body": size(13),
            "bodyLarge": size(15),
            "title": size(17),
            "titleLarge": size(21),
            "display": size(30),
            "hero": size(44),
        },
        "weight": {
            "regular": 400,
            "medium": 500,
            "semibold": 600,
            "bold": 700,
        },
        "letterSpacing": {
            "tight": -0.4,
            "normal": 0.0,
            "wide": 0.35,
        },
        "lineHeight": 1.35,
    }


def _resolve_motion(settings: dict[str, Any], access: dict[str, Any]) -> dict[str, Any]:
    motion = settings.get("motion", {})
    preset_name = str(motion.get("preset", "macos"))
    preset = MOTION_PRESETS.get(preset_name, MOTION_PRESETS["macos"])

    reduced = bool(motion.get("reducedMotion") or access.get("reducedMotion"))
    disabled = bool(access.get("disableAnimations")) or preset_name == "disabled"

    scale = preset["scale"] * _clamp(_num(motion, "speedScale", 1.0), 0.1, 3.0)
    if reduced:
        # Reduced motion is not "no motion": cross-fades still help
        # people track what changed. Shorten and flatten instead.
        scale *= 0.45
    if disabled:
        scale = 0.0

    durations = {
        name: 0 if disabled else max(0, int(round(base * scale)))
        for name, base in BASE_DURATIONS.items()
    }

    return {
        "preset": preset_name,
        "reduced": reduced,
        "disabled": disabled,
        "scale": round(scale, 4),
        "springs": bool(preset["spring"]) and not reduced and not disabled,
        "overshoot": 0.0 if (reduced or disabled) else preset["overshoot"],
        "duration": durations,
        "curve": {name: list(points) for name, points in CURVES.items()},
    }


def _elevation(colors: dict[str, str], glass: dict[str, float]) -> list[dict[str, Any]]:
    """Four shadow levels, scaled by one knob.

    Depth is what stops layered glass from reading as flat decals, so
    each level moves blur, offset and opacity together rather than only
    darkening.
    """
    spread = glass["elevationSpread"]
    strength = glass["shadowStrength"]
    levels = [
        {"name": "flat", "blur": 0, "y": 0, "opacity": 0.0},
        {"name": "raised", "blur": 12, "y": 2, "opacity": 0.18},
        {"name": "floating", "blur": 28, "y": 8, "opacity": 0.28},
        {"name": "overlay", "blur": 48, "y": 16, "opacity": 0.36},
        {"name": "modal", "blur": 72, "y": 26, "opacity": 0.44},
    ]
    return [
        {
            "name": level["name"],
            "blur": round(level["blur"] * spread, 2),
            "y": round(level["y"] * spread, 2),
            "opacity": round(min(1.0, level["opacity"] * strength * 1.8), 4),
            "color": colors["shadow"],
        }
        for level in levels
    ]
