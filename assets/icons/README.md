# Icons and the Halcyon mark

| File | What it is | Where it is used |
|---|---|---|
| `halcyon.svg` | The master mark, as vector. Edit this. | Source for the PNGs below. |
| `halcyon.png` | 256 px raster. | The launcher button in the bar, and the About panel. |
| `halcyon-64.png` | 64 px raster. | Small uses, and icon themes that want a bitmap. |

The mark is three stacked chevrons on a flat tile in the default Halcyon
accent. Its colours are fixed, so it reads the same on a light or dark
wallpaper and does not depend on the theme. It is one flat shape with no
gradients, blend modes or filters, so it stays legible down to about
24 px.

## What the shell loads, and from where

`install.sh` copies this directory to `$HALCYON_DATA_DIR/icons`, which
defaults to `~/.local/share/halcyon/icons`. The shell resolves the same
path through `Config/Paths.qml` (`Paths.logo`), honouring the same
`HALCYON_DATA_DIR` override. If the file is missing, the launcher falls
back to a text glyph and the About panel hides the image; nothing shows a
broken-image box.

## Regenerating the PNGs

Render the SVG with any renderer. The repository has no SVG tool
dependency, so the PNGs were produced with the system Chromium:

```sh
python3 scripts/dev/render-logo.py   # writes halcyon.png and halcyon-64.png
```

## Licence

Everything here is original geometry. No third-party icon set, logo or
trademark is included.
