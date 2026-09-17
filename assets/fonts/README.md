# Fonts

**Nothing is bundled here, deliberately.**

Halcyon uses Inter for the interface, JetBrains Mono for monospace, and
a Nerd Font for the bar's icon glyphs. All three are installed as
packages by `install.sh` (the `fonts-ui`, `fonts-mono` and
`fonts-symbols` roles in `deps/roles.conf`), so they are managed and
updated by your distribution rather than vendored into a dotfiles
repository at whatever version happened to be current.

That also keeps the licensing honest: redistributing a font means
carrying its licence and its obligations, and there is no reason to do
that when every supported distribution already packages these.

## Changing them

```sh
halcyon settings set appearance.fontUi "IBM Plex Sans"
halcyon settings set appearance.fontMono "Iosevka"
halcyon theme apply
```

The family must be installed — `fc-list | grep -i <name>` to check. Icon
glyphs in the bar come from the Material Design set in Nerd Fonts; with
no Nerd Font installed the bar shows boxes where the icons should be.

## Why not an Apple typeface

San Francisco is proprietary and its licence does not permit
redistribution or general desktop use. Inter was chosen because it is
open, actively maintained, and has proportions close to what this design
wants — not as a substitute nobody would notice.
