# Wallpapers

Three originals, generated as PNG at 2560×1440.

| File | Character | Derived accent |
|---|---|---|
| `halcyon-dusk.png` | Deep blue and violet on near-black. | Blue, `#305fd1` |
| `halcyon-dawn.png` | Warm light: amber, pale blue, a touch of mauve. | Amber, `#d89b75` |
| `halcyon-slate.png` | Near-neutral with a teal cast. | Teal, `#157a69` |

Each is built from a few large, soft forms composited in linear light
rather than a gradient with noise over it. That is not a stylistic
preference — the palette extractor scores swatches by chroma, area and
mid-tone preference, so a wallpaper whose colours are all near-grey
produces a dull desktop and one with a dozen competing hues produces an
unstable one. These are shaped to give it one clear answer, which is why
the accents above are what they are.

They are PNG rather than JPEG so the built-in decoder can read them on a
machine with no ImageMagick.

## Using your own

```sh
halcyon wallpaper set ~/Pictures/whatever.png
```

Colours are re-derived automatically unless `wallpaper.deriveColors` is
off. To rotate through a folder:

```sh
halcyon settings set wallpaper.rotation.enabled true
halcyon settings set wallpaper.rotation.directory ~/Pictures/Wallpapers
halcyon settings set wallpaper.rotation.intervalMinutes 30
```

## Regenerating

`scripts/dev/make-wallpapers.py` writes these three files. Editing the
form lists in it and re-running is how to change them.
