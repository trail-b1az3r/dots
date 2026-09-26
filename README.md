# Halcyon

A Hyprland desktop built on [end-4's dots-hyprland](https://github.com/end-4/dots-hyprland)
(illogical-impulse), with a small layer of our own on top.

The earlier Halcyon was a desktop written from scratch: a Python theme
generator, its own Quickshell shell and its own installer. It broke, so
this repository now starts from end-4's desktop, which is maintained and
known to work, and keeps Halcyon's own changes in one place on top of it.

---

## What you get

Everything illogical-impulse provides: the Quickshell bar and sidebars,
overview, search, notifications, lock screen, on-screen keyboard, AI
sidebar, Material You colours taken from your wallpaper, and the
installer for Arch, Fedora, Gentoo and Nix. See the
[illogical-impulse docs](https://ii.clsty.link) for all of it. Those docs
apply here unchanged.

On top of that, Halcyon adds:

| | |
|---|---|
| **Glass panels** | Shell transparency is on by default. It can still be turned off in Settings. |
| **Softer layout** | Wider gaps, rounder corners, deeper blur (popups too), a softer shadow. |
| **Wallpapers** | The hyperNeo fire wallpaper is the default. It and the three Halcyon wallpapers are copied into `~/Pictures/Wallpapers`, where the wallpaper picker looks. |
| **Themes** | Three hand-made themes: HyperNeo, Star Rail and Shattered Glass. [More below.](#themes) |
| **Keybinds** | Extra shortcuts, listed below. They only use key combinations upstream leaves free. |

## Install

```sh
git clone --recursive https://github.com/trail-b1az3r/dots.git halcyon
cd halcyon
./setup install
```

`--recursive` matters. The shell's shape widgets are a git submodule, and
without them Quickshell fails to load. If you already cloned without it:

```sh
git submodule update --init --recursive
```

Useful options (`./setup install -h` lists all of them):

| Option | Effect |
|---|---|
| `--skip-alldeps` | Only copy config. Don't install packages. |
| `--skip-wallpapers` | Don't copy wallpapers into `~/Pictures/Wallpapers`. |
| `--core` | Only Hyprland and Quickshell. Skip fish, fontconfig, misc app config and wallpapers. |

When logging in from a display manager, choose **Hyprland**, not
*Hyprland (uwsm)*.

`./setup uninstall` removes what the installer put in place.

## Themes

By default, colours come from your wallpaper, as in upstream. A theme
replaces that with a palette designed by hand, plus its own window
style, animations, wallpaper and, for some, shell layout and effects:

| Theme | Id | Look |
|---|---|---|
| **HyperNeo** | `hyperneo` | macOS-style, in ember and neon on near-black. A menu bar and a dock, squircle windows with deep soft shadows, springy animations, rounded screen corners. |
| **Star Rail** | `hsr` | Astral gold and lavender on deep-space navy, over a golden rail curving through a nebula. Can show the current banner character. |
| **Shattered Glass** | `shattered-glass` | Liquid glass: a glass lens follows the pointer, clicks crack the screen, windows turn to frosted glass. Ice blue and prism violet, sharp corners. |

Pick one with **`Ctrl + Super + Shift + T`**, or from a terminal:

```sh
~/.config/hypr/hyprland/halcyon/halcyon-theme list
~/.config/hypr/hyprland/halcyon/halcyon-theme apply shattered-glass
~/.config/hypr/hyprland/halcyon/halcyon-theme off     # back to wallpaper colours
```

A theme recolours everything, not just the bar:

- **Shell:** its palette goes straight into the Quickshell colours.
- **Terminals:** its own 16-colour palette.
- **GTK, Qt/KDE, fuzzel and the lock screen:** generated from the theme's
  seed colour through upstream's own pipeline.
- **Windows:** gaps, corners, borders, blur, shadows and animations.
- **Shell layout:** some themes change shell settings too. HyperNeo turns
  on the dock and restyles the bar, and Shattered Glass makes panels more
  see-through. These are put back when you leave the theme, except any
  you changed yourself in the meantime.

Picking another wallpaper leaves the theme, and colours follow the new
wallpaper. The themes are dark themes, so switching to light mode, or
picking an accent colour, also leaves the theme. The colours are then
generated from the theme's accent, not hand-made. `halcyon-theme off`
makes colours follow the wallpaper again.

### Effects

| Level | What you get |
|---|---|
| `full` | Everything, including screen shaders. Shattered Glass's default. |
| `light` | No screen shader. Glass materials, translucent windows and animations stay. The other themes' default. |
| `off` | Plain blur, opaque windows, no native glass, stock animations. |

```sh
halcyon-theme effects light      # or full / off; sticks across themes
halcyon-theme effects default    # back to each theme's own default
```

The menu (`Ctrl + Super + Shift + T`) has the levels too.

**Shattered Glass at `full`** runs a screen shader
(`themes/shaders/shattered-glass.frag`) that treats the screen as a
pane of glass:

- **Pointer lens:** a refracting glass lens follows the pointer, with
  chromatic fringes and a lit rim. It fades when the pointer rests.
- **Click cracks:** each click sends out a refraction wave and cracks the
  glass around the click into shards, which then heal.
- **Edges:** the screen's edges split colour slightly, as thick glass does.

Mouse effects need Hyprland's damage tracking off, so the screen is
redrawn every frame. That uses much more GPU than normal, so use `light`
on battery. The shader needs Hyprland 0.56 or newer. It has been
compile-checked and rendered offline, but not yet tried on a real
display. If the lens looks mirrored vertically,
`halcyon-theme effects flip` fixes it.

**Native glass.** Hyprland's development version, which comes after
0.56, adds built-in glass blur materials. When yours has them, HyperNeo and Shattered Glass switch to
the `acrylic` material automatically, which gives a curved, refracting
glass edge like macOS's Liquid Glass. On 0.56 they use tuned regular
blur instead.

**HyperNeo** has no traffic-light window buttons. Hyprland only draws
those through the hyprbars plugin, which isn't set up here.

### Banners (Star Rail)

The Star Rail theme can show a character on its wallpaper, in a
gacha-banner layout: the character on the right inside a gold frame, and
their name lower left. Point it at art you've saved:

```sh
halcyon-theme banner hsr ~/Pictures/aventurine.png --title "Aventurine"
halcyon-theme banner hsr ~/Pictures/pearl.jpg --title "Pearl" --subtitle "Version 4.6"
halcyon-theme banner hsr --clear
```

- **Cut-out art:** a character with a transparent background stands full
  height on the right.
- **Full splash image:** it fills the right half and fades into the
  nebula.

If Star Rail is active, the banner updates right away.

No character art ships with this repository. It belongs to HoYoverse,
so it can't be released under this repo's GPL licence, and the banner
changes every few weeks anyway. Use art you've saved yourself, for
example the official wallpapers from the game's website.

### Making your own

Copy one of `dots/.config/hypr/hyprland/halcyon/themes/*.json`, rename it
and edit it. The file name is the theme's id. It needs:

- **Shell colours:** the full set, which `halcyon-theme check` lists if
  any are missing.
- **Terminal colours:** 16 of them.
- **Seed colour and scheme:** for the generated app colours.
- **Window settings:** as in the existing themes.
- **Wallpaper:** a path relative to `themes/`, or starting with `~`.

Optional sections, all shown in the shipped themes:

- **More window settings:** squircle power, shadow shape, window opacity,
  `curves` and `animations`.
- **`effects`:** a default level, a screen shader, native glass settings.
- **`shell_config`:** any setting from the shell's `Config.qml`, written
  as dotted keys like `"dock.enable": true`.
- **`banner`:** frame and glow colours.

`halcyon-theme check` rejects a theme with a missing key or a malformed
value, and one where any text colour falls below WCAG AA contrast (4.5:1)
on its background. CI also checks that every `shell_config` key exists
in the shell, and that shaders compile.

The two new wallpapers are procedural and original. No game assets are
used. `scripts/make-theme-wallpapers.py` redraws them.

## Keybinds

These are the ones Halcyon adds. Press `Super + /` in the desktop for the
full list, including all of upstream's.

| Keys | Action |
|---|---|
| `Super + Space` | Search |
| `Super + Escape` | Session menu (lock, log out, power) |
| `Super + ,` | Settings |
| `` Super + ` `` | Back to the previous workspace |
| `Super + Shift + 3` | Screenshot the screen, to clipboard and `~/Pictures/Screenshots` |
| `Super + Shift + 4` | Screenshot a region |
| `Super + Shift + 5` | Record a region |
| `Super + Shift + 6` | Screenshot the focused window, to clipboard and file |
| `Ctrl + Super + Shift + T` | Pick a Halcyon theme |
| `Super + Shift + H` | HyperNix (if installed) |

Upstream's bindings are all still there. For example, `Super + Q` closes
a window, `Super + Enter` opens a terminal, and `Super` on its own opens
search.

## How it's put together

```
dots/.config/hypr/
├── hyprland.lua            entry point: upstream, then Halcyon, then yours
├── hyprland/               upstream defaults (replaced on every install)
│   └── halcyon/            ← the Halcyon layer
│       ├── init.lua          what gets loaded; comment a line out to drop it
│       ├── general.lua       gaps, rounding, blur, shadow
│       ├── keybinds.lua      the extra shortcuts
│       ├── halcyon-theme     the theme tool
│       ├── halcyon-banner    composes banner art into a wallpaper
│       └── themes/           one JSON per theme, their wallpapers and shaders
└── custom/                 your own overrides (never overwritten)
wallpapers/                 copied to ~/Pictures/Wallpapers on install
```

Load order is **upstream defaults → Halcyon → active theme →
`~/.config/hypr/custom`**. The active theme's window style is written to
`~/.local/state/halcyon/theme.lua`.
Anything you put in `custom/` wins over both, so put your changes there,
not in `hyprland/`. The installer replaces `hyprland/` every time.

Outside that folder, Halcyon changes very little in upstream's files:

- `quickshell/ii/modules/common/Config.qml`: transparency on by default
- `quickshell/ii/services/FirstRunExperience.qml`: the welcome text
- `quickshell/ii/assets/images/default_wallpaper.png`: the default wallpaper
- `quickshell/ii/scripts/colors/switchwall.sh`: one line, so a wallpaper change leaves the active theme
- `setup` and `sdata/subcmd-install/`: the wallpaper step, `--skip-wallpapers`, and Halcyon's name in the greeting

Keeping it this small is deliberate: it keeps fixes from upstream easy
to take.

## Taking updates from upstream

```sh
git remote add upstream https://github.com/end-4/dots-hyprland.git
git fetch upstream
git merge upstream/main
git submodule update --init --recursive
./setup install
```

Conflicts, if any, will be in the few files listed above.

## Development

```sh
./scripts/validate.sh
```

CI runs the same script. It checks that:

- every Lua file parses, and every shell script parses;
- all JSON is valid;
- the Halcyon layer is wired in, and the submodule and wallpapers are present;
- every theme is complete, has readable contrast, and renders to valid Lua
  at every effects level;
- every shell setting a theme changes exists in the shell, with the right type;
- screen shaders compile as GLSL ES 3.00, and the banner compositor runs;
- no Halcyon keybind reuses a key combination upstream already binds.

That last check exists because Hyprland runs *every* action bound to a
key combination. A clash would not replace upstream's action; both would
fire at once.

## Credits and licence

The desktop is [end-4](https://github.com/end-4)'s illogical-impulse and
the work of its contributors. Halcyon is a small layer on top of it.
Licensed under the GPL-3.0, like upstream. See [LICENSE](LICENSE). Some
parts carry their own licences, listed in [licenses/](licenses/).
