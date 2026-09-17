# Theming

Halcyon has one source of truth for every visual value. Change it in
`settings.json`, and it lands in Hyprland, Quickshell, Waybar, hyprlock
and hypridle together. There is no second place to keep in sync.

## The colour system

Colour is computed in **OKLab/OKLCh**, not sRGB, because perceptual
lightness is the thing the design actually depends on. In sRGB, "make
this 20% lighter" produces different apparent changes for different
hues; in OKLab it does not.

### From wallpaper to palette

1. **Extract.** ImageMagick's histogram, quantised, when it is
   installed. Otherwise a pure-Python PNG decoder that does its own
   unfiltering — so wallpaper colours work on a minimal install.
2. **Score.** Each swatch by `chroma^0.85 × share^0.35 × midtone`. The
   share term keeps a large area meaningful without letting a flat
   background dominate; the midtone term rejects near-black and
   near-white, which make poor accents.
3. **Clamp.** A swatch from a photograph can be any lightness or chroma.
   A wallpaper-derived accent is clamped to L 0.52–0.74, C 0.09–0.19, so
   it works on both light and dark glass. **An accent you chose by hand
   is used exactly as you chose it** — no clamping.
4. **Derive.** Secondary at +38°, tertiary at −52°, and a neutral that
   keeps a trace of the accent hue so greys feel related to the
   wallpaper rather than laid on top of it.

### Gamut mapping

Pushing a saturated colour to a very different lightness takes it
outside sRGB. Clipping each channel independently — the obvious fix — is
wrong: it moves the hue, and a blue ramp comes back visibly purple at
the light end.

Halcyon instead holds lightness and hue and binary-searches the largest
chroma that fits, which is what CSS Color 4 specifies. The result is a
ramp that reads as one hue from end to end. There is a unit test for
exactly this; it is how the per-channel version was caught.

### Contrast

Every foreground/background pair is checked against WCAG contrast
ratios and corrected if it falls short, by moving lightness while
holding hue. `accessibility.highContrast` raises the floors.

This is why an extreme accent does not produce unreadable text: the
floor is applied after derivation, not hoped for.

## Glass

A surface is not one colour with an alpha. `GlassSurface` layers:

| Layer | What it does |
|---|---|
| Blur | Hyprland's, configured per layer through `layerrule`. |
| Tint | The accent hue, at `glass.tintStrength`. |
| Saturation | Boosts what shows through. Above 1.0 is what stops glass looking grey. |
| Specular | A highlight along the top edge — the thing that reads as *glass* rather than frosted plastic. |
| Inner shadow | Depth at the bottom edge. |
| Border | A hairline that separates the surface from what is behind it. |
| Drop shadow | `MultiEffect`, scaled by elevation. |
| Noise | A trace of grain that hides blur banding on large flat areas. |

### Elevation

Surfaces sit at levels, not at arbitrary depths. A module declares an
elevation; opacity, blur, shadow and border follow from it. That is why
the hierarchy stays consistent when you change one glass value —
everything moves together.

`glass.elevationSpread` controls how far apart the levels sit.

### Presets

| Preset | Character |
|---|---|
| `tinted` | The default. Wallpaper-derived tint; panels feel part of the desktop. |
| `clear` | Transparent but legible. |
| `ultra-clear` | Almost invisible. Heaviest on the GPU — blur has nothing to hide behind. |
| `dark-glass` | Deep and smoky. Good with bright wallpapers. |
| `light-glass` | Frosted white with soft shadows. |
| `oled` | True black, hairline borders, no blur on the largest surfaces. |

```sh
halcyon theme list-presets
halcyon theme preset oled
```

A preset merges into your overrides, so anything you set by hand
afterwards still wins.

## Motion

Five presets over seven named curves, with durations scaled from a
single base.

| Preset | Character |
|---|---|
| `macos` | The default. Emphasised easing, generous durations. |
| `smooth` | Softer, slightly slower. |
| `fast` | Everything shorter. |
| `minimal` | Fades only, no movement. |
| `disabled` | No animation at all. |

Curves: `standard`, `decelerate`, `accelerate`, `emphasised`, `gentle`,
`overshoot`, `linear`. Each has a job — windows opening decelerate,
windows closing accelerate, overlays use `emphasised`.

Every curve's control points are monotonic in x. A bezier whose x
doubles back folds the curve on itself and animates wrong; this is
tested, because one had that problem.

`motion.speedScale` multiplies every duration at once. Below 1.0 is
faster.

Reduced motion (`motion.reducedMotion` or
`accessibility.reducedMotion`) collapses everything to opacity fades
through the token system, not a separate code path — so it cannot drift
out of sync with the rest of the theme.

## Typography

Inter by default: an open typeface with proportions close to what this
design wants, and no licensing questions. JetBrains Mono for monospace.

The type scale is computed, not enumerated. `appearance.fontSizeScale`
multiplies it; `accessibility.textScale` and `accessibility.largeText`
apply on top.

Halcyon does not set `Text.NativeRendering`, which is wrong at
fractional scaling and is the usual cause of blurry text on a scaled
display.

## Writing a preset

A preset is settings sections at the top level plus a `name` and
`description`:

```jsonc
// themes/midnight.json
{
  "name": "Midnight",
  "description": "Indigo accent on near-black glass.",
  "appearance": {
    "mode": "dark",
    "accentSource": "fixed",
    "accentColor": "#5E5CE6"
  },
  "glass": {
    "preset": "dark-glass",
    "opacity": 0.62,
    "tintStrength": 0.1,
    "specularStrength": 0.35
  },
  "graphics": { "blurQuality": "medium" }
}
```

Drop it in `themes/` (in the repository) or
`~/.local/share/halcyon/themes/` (for a local one). It appears in
`halcyon theme list-presets` immediately — there is no registry.

## Inspecting what was generated

```sh
halcyon theme apply --json
cat ~/.config/halcyon/generated/theme.json | python3 -m json.tool | head -40
```

`theme.json` is the token document every surface reads. If something
looks wrong, it is the first place to check — the renderers only project
what is in there.

Do not edit anything in `generated/`. The next settings change
overwrites it.
