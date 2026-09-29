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
| **Themes** | Four hand-made themes: HyperNeo, Star Rail, Shattered Glass and Fractured Glass. [More below.](#themes) |
| **Windows** | Minimise, hide an app, and restore, plus a Windows panel with live previews (`Super + Shift + W`). [More below.](#windows) |
| **Voice assistant** | Press `Super + Shift + Space` and speak. It answers aloud and can run the desktop. [More below.](#voice-assistant) |
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
| **Fractured Glass** | `fractured-glass` | Refraction only, like Apple's Liquid Glass: a squircle glass lens follows the pointer and bends what's behind its rim. No ripples or cracks. Soft blue, lavender and pink over calm fragments of thick glass. |

Pick one in **Settings > Halcyon**, with **`Ctrl + Super + Shift + T`**,
or from a terminal:

```sh
halcyon list
halcyon apply shattered-glass
halcyon off        # back to wallpaper colours
halcyon help       # everything else
```

`halcyon` is an alias in fish and zsh, and a link in `~/.local/bin`
(created when Hyprland starts) for other shells. Open a new terminal
after installing. Until then, the full path is
`~/.config/hypr/hyprland/halcyon/halcyon-theme`.

Applying prints one line. Output from upstream's colour scripts goes to
`~/.local/state/halcyon/apply.log` instead. On Hyprland that log
includes a traceback from end-4's KDE colour syncer
(kde-material-you-colors) about KWin not running. It's harmless: KWin is
KDE's compositor, and Hyprland is doing that job instead.

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
generated from the theme's accent, not hand-made. `halcyon off`
makes colours follow the wallpaper again.

### Effects

| Level | What you get |
|---|---|
| `full` | Everything, including screen shaders. The glass themes' default. |
| `light` | No screen shader. Glass materials, translucent windows and animations stay. The other themes' default. |
| `off` | Plain blur, opaque windows, no native glass, stock animations. |

Set the level in **Settings > Halcyon > Effects**, from the
`Ctrl + Super + Shift + T` menu, or with:

```sh
halcyon effects light      # or full / off; sticks across themes
halcyon effects default    # back to each theme's own default
```

**Settings > Halcyon > Glass** tunes the glass. Changes apply to the
active theme straight away:

| Setting | Default | What it does |
|---|---|---|
| Pointer lens | on | The glass lens that follows the pointer (Full only) |
| Click ripples | on | A soft ripple and faint cracks where you click (Full only) |
| Colour fringe at screen edges | off | Slight colour split at the edges (Full only) |
| Strength | 0.5 | Scales all the screen effects; 0 turns them to nothing |
| Lens size | 90 px | Radius of the pointer lens |
| Lens bounce | 0.6 | How much the lens squashes and springs back; 0 turns it off |
| Focused / other windows | 0.96 / 0.9 | Opacity of glass windows (Light and Full) |
| Frost | 8 | Blur size behind glass windows |

They're stored under `halcyon` in `~/.config/illogical-impulse/config.json`,
which `halcyon refresh` re-reads.

**Shattered Glass at `full`** runs a screen shader
(`themes/shaders/shattered-glass.frag`) that treats the screen as a
pane of glass:

- **Pointer lens:** a liquid-glass lens follows the pointer. Its middle
  stays clear; light bends in its rounded rim, which catches a soft
  highlight on top and a faint shadow below. It fades when the pointer
  rests.
- **Click ripples:** each click sends a gentle ripple through the glass,
  with faint cracks around the click that heal as it passes.
- **Edges (off by default):** the screen's edges split colour slightly,
  as thick glass does.

Mouse effects need Hyprland's damage tracking off, so the screen is
redrawn every frame. That uses much more GPU than normal, so use `light`
on battery. The shader needs Hyprland 0.56 or newer. It has been
compile-checked and rendered offline, but not yet tried on a real
display. If the lens looks mirrored vertically,
`halcyon effects flip` fixes it.

**Fractured Glass at `full`** runs `themes/shaders/liquid-glass.frag`: a
lens shaped and lit like Apple's Liquid Glass controls. It is a squircle,
with an almost untouched middle and a rounded bezel that bends light more
and more towards the edge, so content wraps around the rim. The rim
catches light facing the top-left, with a dimmer reflection opposite and
a little colour in the inner bezel. The glass lifts saturation slightly
and sits on a soft shadow. Nothing reacts to clicks. Strength and lens
size come from Settings > Halcyon > Glass, like Shattered Glass; the
ripple and edge-fringe switches don't apply to it.

**Native glass.** Hyprland's development version, which comes after
0.56, adds built-in glass blur materials. When yours has them, HyperNeo and Shattered Glass switch to
the `acrylic` material automatically, which gives a curved, refracting
glass edge like macOS's Liquid Glass. On 0.56 they use tuned regular
blur instead.

**HyperNeo** has no traffic-light window buttons. Hyprland only draws
those through the hyprbars plugin, which isn't set up here.

**Lens bounce.** Both glass lenses are a little springy:
- **While moving:** the lens is pressed slightly flatter and quivers.
- **When the pointer stops:** it springs back past its rest shape, trading
  width for height a couple of times, then settles in about half a second.

Hyprland gives screen shaders the time since the pointer last moved, but
not its speed or direction, so the bounce follows that timing. It doesn't
lean into the direction of travel.

### Cursor

Halcyon has its own cursor, **Halcyon Glass**. It matches the glass
themes: a dark glass body, a white outline, a blue-to-lavender glint
inside the rim, and a soft shadow. There are 24 shapes (arrow, hand,
text, resize arrows, grab, zoom, and more), with an animated spinner for
busy and progress, covering 117 cursor names in all. It ships in both
formats: XCursor for X11/XWayland and GTK apps, and hyprcursor for
Hyprland itself.

It's on by default and follows any theme, including wallpaper colours.
Turn it off, or change its size, in **Settings > Halcyon > Cursor**, or:

```sh
halcyon cursor off        # back to illogical-impulse's Bibata cursor
halcyon cursor size 32
```

Every shape is drawn from scratch in `scripts/make-cursors.py`, which
rebuilds the theme into `dots/.local/share/icons/Halcyon-Glass`
(it needs cairosvg and Pillow).

### Banners (Star Rail)

The Star Rail theme can show a character on its wallpaper, in a
gacha-banner layout: the character on the right inside a gold frame, and
their name lower left. Point it at art you've saved:

```sh
halcyon banner hsr ~/Pictures/aventurine.png --title "Aventurine"
halcyon banner hsr ~/Pictures/pearl.jpg --title "Pearl" --subtitle "Version 4.6"
halcyon banner hsr --clear
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

- **Shell colours:** the full set, which `halcyon check` lists if
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

`halcyon check` rejects a theme with a missing key or a malformed
value, and one where any text colour falls below WCAG AA contrast (4.5:1)
on its background. CI also checks that every `shell_config` key exists
in the shell, and that shaders compile.

The theme wallpapers are procedural and original. No game assets are
used. `scripts/make-theme-wallpapers.py` redraws them.

## Windows

Hyprland has no "minimised" state, so Halcyon adds one. It is a better
version of the original Halcyon's window manager. Minimised windows go to
a hidden special workspace, and a stack remembers where each one came
from, so restoring puts a window back on its own workspace. If that
workspace is gone, the window comes back to the one you're on.

| Keys | Action |
|---|---|
| `Super + Shift + W` | Windows panel |
| `Ctrl + Super + M` | Minimise the focused window |
| `Ctrl + Super + Shift + M` | Restore the last minimised window |
| `Ctrl + Super + H` | Hide the focused app (all its windows), like ⌘H |
| `Ctrl + Super + Alt + H` | Hide every other window on this workspace, like ⌥⌘H |

**The Windows panel** shows every open window as a live preview, most
recently used first. Minimised windows sit on a shelf underneath.

- Typing filters by title or app.
- The arrows or Tab move the selection. Enter focuses the window, or
  restores it if it was minimised.
- `Ctrl` + `M` minimises, `H` hides the app, `F` floats or tiles, `P`
  pins to every workspace, `C` centres, and `Q` closes. `Delete` also
  closes when the filter is empty.
- Hovering a preview shows the same actions as buttons. Middle-click
  closes a window.
- On the shelf, click a window to restore it, or right-click to close it.
  **Restore all** brings every minimised window back.

The same actions work from a terminal, or from your own binds in
`~/.config/hypr/custom`:

```sh
halcyon windows list            # open and minimised windows (--json for scripts)
halcyon windows minimise        # or: hide, hide-others, restore, restore --all
halcyon windows close 0x5d3a...  # focus, close, float, pin or centre by address
```

The voice assistant can do this too ("minimise this", "bring my windows
back").

## Voice assistant

Press **`Super + Shift + Space`**, say what you want, and stop talking.
Halcyon answers in a notification and out loud. Press the shortcut again
to cancel. Turn on **"Hey Halcyon"** in **Settings > Halcyon > Assistant**
to start it by voice instead.

**One-time setup** (speech recognition, about 300 MB):

```sh
halcyon assistant setup            # add --wake for "Hey Halcyon", --piper for a natural voice
halcyon assistant login            # use your Claude Pro/Max plan: no API key needed
halcyon assistant doctor           # what's ready and what isn't
```

Or use an API key instead: `halcyon assistant key anthropic` (or `gemini`,
`openai`, `mistral`), or a key already entered in the AI sidebar.

### Using a Claude Pro or Max plan

Anthropic doesn't let other apps sign in with a claude.ai account or reuse
its login. The supported way to use a plan outside claude.ai is
**Claude Code**, Anthropic's own CLI, so that's what Halcyon uses.
`halcyon assistant login`, or **Sign in with Claude** in
**Settings > Halcyon > Assistant**, does the following:

1. Offers to install Claude Code with Anthropic's installer if it's
   missing (it asks first).
2. Runs Claude Code's own sign-in (`claude auth login`), which opens
   claude.ai in your browser. Halcyon never sees your login.
3. Switches the assistant to **Claude plan**.

After that, each request runs Claude Code headless (`claude -p`), locked
down so the only things it can do are Halcyon's desktop actions:

- all of its built-in tools are off: no shell, no files;
- it loads no MCP servers except Halcyon's, which serves the same
  twelve checked actions as every other provider;
- any `ANTHROPIC_API_KEY` in the environment is removed for the call, so
  your plan is what gets used.

Requests count against your plan's usage limits. The model is whatever
your plan's Claude Code uses; `halcyon assistant set model opus` picks
another.

**What happens:**

1. The microphone records until you pause (PipeWire).
2. **Whisper** turns your speech into text on this computer; the audio
   never leaves your machine.
3. The text goes to the AI you chose: **Claude on your Pro/Max plan**
   (through Claude Code), **Claude with an API key** (`claude-opus-5`),
   **Gemini**, a local **Ollama** model, or any **OpenAI-compatible**
   server. *Auto* picks an Anthropic API key if set, then your Claude
   plan, then Gemini, then Ollama. Keys are shared with end-4's AI sidebar, so one entered
   there works here too.
4. The reply appears in a notification and is spoken, with Piper if you
   set it up, otherwise espeak-ng.

**What it can do.** Only these actions, each checked against a strict
schema before anything runs:

- open an app by name;
- set or change volume, mute speakers or the microphone, set brightness;
- control media;
- switch workspace;
- minimise, hide or restore windows, or open the Windows panel;
- change the Halcyon theme or effects level;
- take a screenshot, lock the screen, or search the web.

It can't run commands or scripts, and nothing it says is ever given to a
shell. Turn actions off entirely with **Let it control the desktop**.

**The wake word** is spotted by a small offline Vosk model that only
knows the phrase. It keeps the microphone open while it's on, so it's
off by default.

**Settings > Halcyon > Assistant** covers the provider, wake word, spoken
replies, desktop control and recognition accuracy. Anything else:

```sh
halcyon assistant set model claude-sonnet-5   # or any model your provider offers
halcyon assistant set provider openai && halcyon assistant set endpoint http://localhost:8080/v1
halcyon assistant ask "what's on workspace 3?"  # typed, prints the reply
```

It keeps a few minutes of conversation, so follow-ups work, and logs to
`~/.local/state/halcyon/assistant.log`.

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
| `Super + Shift + Space` | Voice assistant (again to cancel) |
| `Super + Shift + W` | Windows panel ([minimise, hide and restore keys](#windows)) |
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
│       ├── halcyon-theme     the theme tool (the `halcyon` command)
│       ├── halcyon-banner    composes banner art into a wallpaper
│       ├── halcyon-windows   minimise, hide and restore (`halcyon windows`)
│       ├── assistant/        the voice assistant (halcyon-assistant + its Python package)
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
- `quickshell/ii/modules/common/Config.qml`: the `halcyon` settings, and `settings.qml` plus `modules/settings/HalcyonConfig.qml` for the Halcyon settings page
- `quickshell/ii/modules/ii/windowManager/` (new), plus one line each in `GlobalStates.qml` and `panelFamilies/IllogicalImpulseFamily.qml`: the Windows panel
- `fish/config.fish` and `zshrc.d/dots-hyprland.zsh`: the `halcyon` alias
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
- every setting in the rendered Lua exists in Hyprland 0.56.2 with a value
  of the right type, using the option table in `scripts/data/`, which was
  extracted from Hyprland's source;
- every shell setting a theme changes exists in the shell, with the right type;
- screen shaders compile as GLSL ES 3.00, and the banner compositor runs;
- the cursor theme's XCursor files, hyprcursor zips and aliases are well formed and cover the essential names;
- the voice assistant's tests pass (`tests/`): end-of-speech detection, action validation, every provider's request and reply format, the tool loop, and settings.
- no Halcyon keybind reuses a key combination upstream already binds.

That last check exists because Hyprland runs *every* action bound to a
key combination. A clash would not replace upstream's action; both would
fire at once.

## Credits and licence

The desktop is [end-4](https://github.com/end-4)'s illogical-impulse and
the work of its contributors. Halcyon is a small layer on top of it.
Licensed under the GPL-3.0, like upstream. See [LICENSE](LICENSE). Some
parts carry their own licences, listed in [licenses/](licenses/).
