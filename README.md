# Halcyon

A desktop environment for Hyprland — not a theme on top of one.

Halcyon takes the ideas behind Apple's Liquid Glass — layered
translucency, material that responds to what is behind it, motion that
carries meaning — and builds them natively on Wayland. Everything here
is original: the colour system, the glass compositing, the shell, the
search, the assistant. Nothing is copied from Apple, and no proprietary
asset ships in this repository.

The design principle throughout: **one set of tokens, every surface.**
A colour, a radius or a duration is defined once and projected into
Hyprland's Lua config, Waybar's GTK3 CSS, Quickshell's QML, hyprlock's
hyprlang and the wallpaper daemon. There is no second place where a
value can drift.

---

## Contents

- [What you get](#what-you-get)
- [Requirements](#requirements)
- [Installation](#installation)
- [Supported distributions](#supported-distributions)
- [Keyboard shortcuts](#keyboard-shortcuts)
- [Architecture](#architecture)
- [Customisation](#customisation)
- [The AI assistant](#the-ai-assistant)
- [HyperNix integration](#hypernix-integration)
- [Battery and power](#battery-and-power)
- [Environment variables](#environment-variables)
- [Troubleshooting](#troubleshooting)
- [Uninstalling and restoring](#uninstalling-and-restoring)
- [Extending Halcyon](#extending-halcyon)
- [Development](#development)
- [Licence](#licence)

---

## What you get

**A shell, written in Quickshell.** A floating bar, Spotlight-style
universal search, a Control Center, a notification centre with grouping
and history, Mission Control, an application switcher, on-screen
displays for volume and brightness, a lock screen with real PAM
authentication, and desktop widgets. 78 QML files, no placeholder
components.

**Glass that is actually composited.** `GlassSurface` layers a tint, a
specular highlight, an inner shadow, a hairline border and a drop shadow
over Hyprland's blur, with the layer's own blur configured through
`layerrule`. Six presets — `tinted`, `clear`, `ultra-clear`,
`dark-glass`, `light-glass` and `oled` — each a different balance of
opacity, blur radius, saturation and specular strength, not six opacity
values.

**Colour derived from your wallpaper.** Swatches are extracted (via
ImageMagick, or a pure-Python PNG decoder when it is not installed),
scored by chroma, area and mid-tone preference, then projected through
OKLCh into a full tonal ramp. Out-of-gamut colours are mapped by
reducing chroma at constant hue, the way CSS Color 4 specifies — so a
ramp reads as one hue from end to end instead of drifting purple at the
light end. Every foreground/background pair is checked against WCAG
contrast ratios and corrected if it falls short.

**Motion with a grammar.** Five presets — `macos`, `smooth`, `fast`,
`minimal`, `disabled` — over seven named curves, with durations scaled
from a single base. Windows, workspaces, layers and menus each
use the curve that matches what they are doing. `prefers-reduced-motion`
and the accessibility settings collapse the whole system to opacity
fades without a separate code path.

**Universal search.** 14 providers — applications, open windows,
settings (searchable by their own labels), desktop actions, files,
recent files, clipboard history, shell commands, power profiles,
HyperNix, a safe calculator, unit and currency conversion, the
assistant, and the web. Time-budgeted, so a slow provider cannot make
the field stutter, and each one isolated so a broken provider cannot
take Spotlight down.

**A voice assistant with two real backends.** NixOrb if you have it, a
local Whisper + Ollama + Piper stack if you do not, switchable from
Settings with no config editing. Deterministic intent rules run before
any model does, so "turn the volume down" never needs an LLM. Every
effect goes through an allowlist of 33 typed actions — the model
chooses an action and its parameters, never a shell command.

**Power management that changes how the desktop looks.** Effects step
down as the battery falls, polling slows, and the policy only ever
reduces quality from what you chose — it will not decide you meant
`high` when you set `low`.

---

## Requirements

| | |
|---|---|
| Compositor | Hyprland **0.56 or newer** (Lua configuration) |
| Shell | Quickshell **0.3 or newer** |
| Bar | Waybar 0.11+ (GTK3) |
| Session | Wayland, PipeWire, a working portal |
| Python | 3.9 or newer, standard library only |

Hyprland 0.53 moved configuration to Lua and 0.56 is the version this
targets. Halcyon reads the option table from your *installed* compositor
via `hyprctl descriptions -j` and validates everything it generates
against it before writing a file — so it adapts to your version rather
than assuming one. When Hyprland is not running (during installation, or
from a TTY) it falls back to a snapshot of 0.56.2's 353 options shipped
in `deps/hyprland-options.json`, and says which source it used.

Optional, by feature:

| Feature | Needs |
|---|---|
| Clipboard history | `cliphist`, `wl-clipboard` |
| Screen recording | `wf-recorder` or `gpu-screen-recorder` |
| Wallpaper colours | `imagemagick` (falls back to a built-in PNG reader) |
| Local assistant | `ollama`, `whisper.cpp`, `piper` |
| NixOrb assistant | `nixorb` |
| Power profiles | `power-profiles-daemon`, `tuned` or `tlp` — **one of them** |

Run `./check-deps.sh` to see what is present on your machine, grouped by
what it would enable.

---

## Installation

```sh
git clone https://github.com/trail-b1az3r/dots.git halcyon
cd halcyon
./install.sh --dry-run     # see the plan for this machine first
./install.sh
```

`--dry-run` prints every package, every file and every service it would
touch, and writes nothing.

### Options

| Flag | Effect |
|---|---|
| `-n`, `--dry-run` | Print the plan; change nothing. |
| `-y`, `--yes` | Do not prompt. |
| `--no-deps` | Do not install system packages. |
| `--no-optional` | Only what the desktop cannot start without. |
| `--with-ai` | Also install the local AI stack. |
| `--no-services` | Do not enable systemd user units. |
| `--no-build` | Never build from source; skip what has no package. |
| `--config-only` | Dotfiles only — no packages, no builds. |
| `--nix-imperative` | On NixOS, use `nix-env` instead of writing a module. |
| `--prefix PATH` | Where built binaries go (default `~/.local`). |
| `-v`, `--verbose` | Print every command. |

### What the installer will not do

It will not overwrite anything without saving it first. Before a single
file is written it creates
`~/.local/state/halcyon/backups/<timestamp>/` and records a manifest of
every path it touches — including paths that did *not* exist, so a
restore knows to remove them rather than leave them behind.

It is idempotent. Running it twice backs up nothing the second time and
reports zero files installed, because it compares content before
writing.

It never configures two power daemons at once — if it finds
`power-profiles-daemon` and `tlp` both active it stops and tells you,
rather than adding a third opinion.

It does not apply GPU environment variables blindly. Hardware is
detected from sysfs vendor IDs (with `lspci` as a fallback), and NVIDIA
variables are only written when the proprietary driver is actually
loaded.

### After installing

Log out and pick **Halcyon** from your display manager, or from a TTY:

```sh
Hyprland
```

Then `Super + /` for the shortcut reference, and `Super + ,` for
Settings.

---

## Supported distributions

| Family | Package manager | Notes |
|---|---|---|
| Arch, EndeavourOS, CachyOS | `pacman` + an AUR helper | Best coverage; Quickshell from AUR. |
| Fedora, Nobara | `dnf` (+ COPR) | Quickshell built from source. |
| Debian, Ubuntu, Pop!_OS | `apt` | Hyprland 0.56 usually needs a backport or a source build. |
| NixOS | a generated module, or `nix-env -i` | See below. |
| openSUSE Tumbleweed | `zypper` | |

Every role in `deps/roles.conf` has an entry in every package map, and
the validator fails if one is missing — so "supported" means the mapping
exists, not that it was assumed.

**On NixOS**, the installer writes a module to
`~/.config/halcyon/nixos/halcyon.nix` and tells you how to import it,
rather than mutating system state behind your back. `--nix-imperative`
uses `nix-env` instead if you prefer.

Building Quickshell from source is pinned to `v0.3.1` and probes for
optional features with `pkg-config` first, disabling what is not
available rather than failing the build.

---

## Keyboard shortcuts

A Linux-native layout. It borrows the macOS capture shortcuts because
`Super+Shift+3/4/5` is genuinely good muscle memory, and it deliberately
does not borrow anyone's tiling bindings.

Because `Super+Shift+<digit>` is taken by capture, **move-to-workspace
is `Super+Ctrl+<digit>`**, not `Super+Shift+<digit>`.

### System

| Shortcut | Action |
|---|---|
| `Super + Space` | Spotlight search |
| `Super + Shift + Space` | Ask the assistant |
| `Super + A` | Assistant push-to-talk |
| `Super + Shift + A` | Cancel the assistant |
| `Super + C` | Control Center |
| `Super + N` | Notification centre |
| `Super + E` | Mission Control |
| `Super + Tab` | Application switcher |
| `Super + K` | Calendar |
| `Super + D` | Desktop widgets |
| `Super + V` | Clipboard history |
| `Super + ,` | Settings |
| `Ctrl + /` | Shortcut reference (also `Super + /`) |
| `Super + Escape` | Power menu |
| `Super + Ctrl + Q` | Lock the screen |
| `Super + Ctrl + R` | Reload the desktop |
| `Super + Shift + T` | Toggle light / dark |
| `Super + Shift + N` | Toggle Do Not Disturb |
| `Super + Shift + W` | Next wallpaper |
| `Super + Shift + P` | Cycle power profile |

### Windows

| Shortcut | Action |
|---|---|
| `Super + W` | Close |
| `Super + Alt + W` | Force quit |
| `Super + M` | Minimise |
| `Super + H` | Hide application |
| `Super + Shift + M` | Restore last minimised |
| `Super + F` | Fullscreen |
| `Super + Shift + F` | Maximise |
| `Super + T` | Toggle floating |
| `Super + Ctrl + C` | Centre |
| `Super + Ctrl + P` | Pin above others |
| `Super + J` | Toggle split direction |
| `Super + ←→↑↓` | Focus |
| `Super + Shift + ←→↑↓` | Move window |
| `Super + Alt + ←→↑↓` | Resize |

### Workspaces

| Shortcut | Action |
|---|---|
| `Super + 1…0` | Switch to workspace |
| `Super + Ctrl + 1…0` | Move window to workspace |
| `Super + Ctrl + ←→` | Previous / next workspace |
| `Super + \`` | Back and forth |
| `Super + S` | Scratchpad |
| `Super + Shift + S` | Move window to scratchpad |
| `Super + Ctrl + ↑↓` | Focus next / previous monitor |

### Capture

| Shortcut | Action |
|---|---|
| `Super + Shift + 3` | Screenshot the screen |
| `Ctrl + Shift + S` | Screenshot a region (also `Super + Shift + 4`) |
| `Super + Shift + 5` | Screenshot & recording panel |
| `Super + Shift + 6` | Screenshot the window |

### Applications

| Shortcut | Action |
|---|---|
| `Super + Return` | Terminal |
| `Super + Shift + Return` | File manager |
| `Super + B` | Browser |
| `Super + Shift + H` | HyperNix |

Media and brightness keys work as labelled. Every binding is defined in
`config/system/keybinds.catalog.json` and can be overridden per-binding
in Settings; set one to `"none"` to unbind it. The generator refuses to
emit two binds for the same chord and writes a comment saying which one
lost.

---

## Architecture

```
settings.json  ──┐
wallpaper      ──┼──▶  palette  ──▶  tokens  ──┬──▶  hypr-theme.lua
defaults       ──┘      (OKLCh)     (theme.py) ├──▶  hypr-runtime.lua
                                               ├──▶  hypr-keybinds.lua
                                               ├──▶  waybar-config.jsonc
                                               ├──▶  waybar-colors.css
                                               ├──▶  theme.json  ──▶ Quickshell
                                               ├──▶  hyprlock-colors.conf
                                               └──▶  hypridle-timeouts.conf
```

One function, `pipeline.apply()`, runs that whole chain and then reloads
whatever is running. Everything that changes the desktop's appearance
goes through it, so "did that take effect?" has one answer.

| Directory | What is in it |
|---|---|
| `src/halcyon/` | The Python core: colour, tokens, renderers, actions, search, power, assistant. Standard library only. |
| `config/hypr/` | Hyprland's Lua configuration, split into appearance, behaviour and autostart. |
| `config/quickshell/` | The shell — `Config`, `Services`, `Components`, `Modules`. |
| `config/waybar/` | Module definitions; the config and CSS are generated. |
| `config/system/` | Settings defaults and the keybind catalog. |
| `scripts/lib/` | Shell libraries: detection, packages, backup, build, menus. |
| `deps/` | Per-distro package maps, role definitions, the Hyprland option snapshot. |
| `services/` | systemd user units, bound to `halcyon-session.target`. |
| `tests/` | 128 unit tests. |

### Why Lua, and why split

Hyprland 0.56 scopes errors per `require()`. Splitting the config means
a typo in `appearance.lua` does not take `behaviour.lua` — and your
keybinds — down with it. `generated.lua` goes further: if the generated
files fail to load, it installs an emergency binding set so you can
always open a terminal and fix it.

Your own overrides go in `~/.config/hypr/local.lua`, loaded last through
`pcall`. It is never overwritten and never backed up over.

### The action allowlist

The assistant cannot run commands. It can name one of 33 registered
actions and supply parameters, which are then type-checked, range-
checked, pattern-checked and — for paths — confined to your home
directory and mounted volumes. `shell=True` appears nowhere. Undeclared
parameters are rejected rather than ignored. Destructive actions
(suspend, reboot, shut down, log out) require explicit confirmation,
and web access is gated on a setting that is off by default.

### Graceful degradation

If Quickshell is not running, `Super + Space` still opens a search —
`shell.call_or_fallback()` routes Spotlight, the power menu, network and
audio to `fuzzel`/`wofi`/`rofi`/`tofi`/`bemenu`/`dmenu`, whichever is
installed. The desktop stays usable while you fix the shell.

---

## Customisation

Everything is in `~/.config/halcyon/settings.json`, and every key has a
typed default in `config/system/settings.default.json`. Only your
overrides are written — the file stays small and readable.

```sh
halcyon settings get appearance.mode
halcyon settings set glass.preset oled
halcyon settings set motion.speedScale 0.8
halcyon settings unset glass.preset      # back to the default
halcyon theme apply                       # regenerate and reload
```

Invalid values are refused with the reason, not silently coerced.

### The sections

| Section | Controls |
|---|---|
| `appearance` | Light/dark, sunset following, accent source and colour, icon and cursor themes, fonts, corner style. |
| `glass` | Preset, opacity, blur strength, saturation, tint, border opacity, corner radius, shadow, padding, specular, refraction, noise. |
| `motion` | Preset, speed scale, reduced motion, overlay animations. |
| `bar` | Position, height, margins, floating, per-monitor, and the module layout for each side. |
| `workspaces` | Count, per-monitor, persistent, wrap-around, names, smart gaps. |
| `input` | Keyboard layout and repeat, focus-follows-mouse, sensitivity, acceleration, natural scroll, tap-to-click, gestures. |
| `displays` | Per-monitor mode/scale/position, VRR, tearing. |
| `graphics` | Blur, shadow and animation quality; transparency; low-power mode; unfocused FPS cap; GPU overrides. |
| `wallpaper` | Path, fit mode, dim, blur, per-monitor, rotation, colour derivation. |
| `notifications` | Position, DND, per-urgency timeouts, grouping, history. |
| `power` | Profile, backend, adaptive thresholds, idle timings, poll intervals. |
| `assistant` | Provider, voice, microphone, wake word, privacy, local model settings, NixOrb settings. |
| `hypernix` | Enable, widget, Spotlight, tray, job notifications, poll interval. |
| `search` | Result limit, per-provider toggles, file roots and depth, web search engine. |
| `applications` | Default terminal, browser, file manager, editor, capture directories. |
| `accessibility` | Reduced motion, high contrast, large text, text scale, disable blur/animations, minimum transparency, focus ring. |
| `privacy` | Clipboard history and limit, recent files, telemetry (off, and there is nothing to send). |
| `keybinds` | Per-binding overrides, keyed by catalog ID. |

### Presets

A preset is a JSON file of settings overrides. Six ship with Halcyon:

| Preset | What it is for |
|---|---|
| `tinted` | The default. Glass carries a wallpaper-derived tint. |
| `clear` | Transparent but legible; the wallpaper stays part of the composition. |
| `ultra-clear` | Almost invisible surfaces. Heaviest on the GPU — the blur has nothing to hide behind. |
| `dark-glass` | Deep, smoky surfaces. For low-light rooms and bright wallpapers. |
| `light-glass` | Frosted white surfaces with soft shadows. |
| `oled` | True black, hairline borders, no blur on the largest surfaces. Saves panel power. |

```sh
halcyon theme list-presets
halcyon theme preset oled
```

Applying a preset merges it into your overrides, so anything you set by
hand afterwards still wins. Dropping a file into `themes/` (or
`~/.local/share/halcyon/themes/`) makes it available immediately — there
is no registry to update. The format is settings sections at the top
level, plus a `name` and `description`:

```jsonc
// themes/midnight.json
{
  "name": "Midnight",
  "description": "Indigo accent on near-black glass.",
  "appearance": { "mode": "dark", "accentSource": "fixed",
                  "accentColor": "#5E5CE6" },
  "glass": { "preset": "dark-glass", "opacity": 0.62 }
}
```

---

## The AI assistant

Two backends, both real, both switchable from
**Settings → AI Assistant → Provider** with no file editing:

- **NixOrb** — a thin adapter over the NixOrb socket, falling back to
  its CLI. It talks to whatever NixOrb exposes on your machine; nothing
  about its interface is faked or stubbed.
- **Local AI** — Whisper (or `whisper.cpp`) for speech, Ollama or any
  OpenAI-compatible endpoint for language, Piper (falling back to
  `espeak-ng`) for speech. Entirely offline.
- **Automatic** — NixOrb when it answers, local otherwise.

Both can be installed at once; they coexist and the daemon routes per
request.

### How a request is handled

1. Audio is captured locally (`pw-record`, `parecord` or `arecord`) with
   silence detection, so it stops when you do.
2. Speech becomes text locally.
3. **Deterministic rules run first.** "Set the volume to 30%", "open
   Firefox", "go to the second workspace" match a rule, become a typed
   action, and execute. No model runs and no text leaves the machine.
4. Only if nothing matches does the model see the request.
5. If the model wants to act, it names an allowlisted action with typed
   parameters. Those are validated before anything happens.
6. Destructive actions stop and ask.

### Privacy

Nothing is uploaded silently. Web access, screen context and clipboard
context are each a separate setting, each **off by default**. With the
local backend and those left off, no audio, text or screen content
leaves the machine at all. Conversation history is local, capped, and
can be cleared with `halcyon assistant clear`.

The daemon listens on a Unix socket in `$XDG_RUNTIME_DIR`, mode `0600`
— not a TCP port.

### Setting up the local stack

```sh
./install.sh --with-ai
ollama pull llama3.2:3b
halcyon settings set assistant.provider local
halcyon assistant status
```

Point it at a different model or an OpenAI-compatible server:

```sh
halcyon settings set assistant.local.llmModel qwen2.5:7b
halcyon settings set assistant.local.llmBackend openai
halcyon settings set assistant.local.llmHost http://127.0.0.1:8080
```

### Setting up NixOrb

```sh
halcyon settings set assistant.provider nixorb
halcyon assistant status          # shows which backend answered
```

If NixOrb's socket is somewhere non-standard, set
`assistant.nixorb.socketPath`.

### Using it

`Super + A` to talk, `Super + Shift + Space` to type, or from anywhere:

```sh
halcyon assistant ask "what's my battery at"
halcyon assistant listen
halcyon assistant providers
```

---

## HyperNix integration

Off unless HyperNix is present. When it is, you get a Control Center
widget with generation and job state, Spotlight entries for its
commands, a tray item, and notifications when a job finishes.

```sh
halcyon settings set hypernix.enabled false   # turn it off entirely
```

Turning it off removes the widget, the Spotlight provider and the tray
item, and changes nothing else. The rest of the desktop does not know it
exists — no shared state, no shared code path.

---

## Battery and power

Halcyon drives exactly one power backend, preferring
`power-profiles-daemon` (the only one of the three with a real switching
API rather than a config file), then `tuned`, then `tlp`. If it finds
two running it refuses to configure either and tells you which to
disable. `halcyon doctor` reports conflicts.

On battery, the adaptive policy steps effects down:

| Battery | What changes |
|---|---|
| On AC | Nothing. Everything at your chosen quality. |
| On battery, above the threshold | Blur drops one step. |
| Below `batteryThreshold` (25%) | Blur down two steps, shadows and animations one, low-power graphics on, profile to battery-saver. |
| Below `criticalThreshold` (10%) | Blur and shadows off, animations minimal. |

The policy **only ever reduces**. Set blur to `low` on a desktop and
nothing will raise it.

Polling slows on battery too — Waybar modules are signal-driven rather
than polled where possible, and the intervals for what must be polled
are separate for AC and battery.

```sh
halcyon power status
halcyon power profile balanced
halcyon settings set power.adaptive.enabled false
halcyon settings set power.adaptive.batteryThreshold 15
```

Unfocused windows are capped to 10 FPS by default
(`graphics.renderUnfocusedFps`), which is the single largest saving on a
laptop.

---

## Environment variables

Read at startup; set them in your shell profile or the systemd user
environment.

### Paths

| Variable | Default | Meaning |
|---|---|---|
| `HALCYON_CONFIG_DIR` | `~/.config/halcyon` | Settings and themes. |
| `HALCYON_GENERATED_DIR` | `$HALCYON_CONFIG_DIR/generated` | Generated config. Do not edit; it is overwritten. |
| `HALCYON_STATE_DIR` | `~/.local/state/halcyon` | Backups, history, logs. |
| `HALCYON_CACHE_DIR` | `~/.cache/halcyon` | Palettes, thumbnails, exchange rates. |
| `HALCYON_DATA_DIR` | `~/.local/share/halcyon` | Installed data files. |
| `HALCYON_PREFIX` | `~/.local` | Where built binaries go. |
| `HALCYON_WALLPAPER_DIR` | `~/Pictures/Wallpapers` | Wallpaper rotation source. |

### Installer

| Variable | Meaning |
|---|---|
| `HALCYON_DRY_RUN` | `1` changes nothing; same as `--dry-run`. |
| `HALCYON_ASSUME_YES` | `1` skips prompts; same as `--yes`. |
| `HALCYON_DEBUG` | `1` adds debug logging. |
| `HALCYON_LOG_FILE` | Where to append the install log. |
| `HALCYON_BACKUP_DIR` | Override the backup root. |
| `HALCYON_PYTHON` | Python interpreter to use. |
| `HALCYON_AUR_HELPER` | Force `paru`, `yay`, … |
| `HALCYON_BUILD_ROOT` | Where source builds happen. |
| `HALCYON_QUICKSHELL_REPO` / `_REF` | Build a different Quickshell (default `v0.3.1`). |

### Detection overrides

`HALCYON_DISTRO_ID`, `HALCYON_FAMILY`, `HALCYON_PKG_MANAGER`,
`HALCYON_GPU_PRIMARY`, `HALCYON_GPU_VENDORS`, `HALCYON_POWER_BACKEND`.
Set these only when detection gets it wrong — they bypass the checks
that keep the installer safe.

### Runtime

| Variable | Meaning |
|---|---|
| `HALCYON_THEME` | Theme to apply at startup. |
| `XDG_RUNTIME_DIR` | Where the assistant socket and IPC live. |

---

## Troubleshooting

Start here:

```sh
./diagnose.sh            # a full report: versions, services, config errors
halcyon doctor           # the same checks, from the CLI
hyprctl configerrors     # Hyprland's own view
```

**The bar or shell is missing.**

```sh
systemctl --user status halcyon-bar halcyon-shell
journalctl --user -u halcyon-shell -n 50
qs -c halcyon             # run the shell in the foreground to see errors
```

**Colours look wrong, or a change did not take.** The generated files
are the source of truth for what is running:

```sh
halcyon theme apply --json     # what was written, and what reloaded
ls ~/.config/halcyon/generated/
```

**Hyprland starts but the desktop is bare.** When the generated files
fail to load, `generated.lua` binds `Super + Return` (a terminal),
`Super + W` (close a window) and `Super + Ctrl + Escape` (log out), and
raises a notification saying so — enough of a desktop to fix it from.
Then:

```sh
hyprctl configerrors
./scripts/dev/check-hypr-config.py
```

**Blur is heavy, or the desktop feels slow.**

```sh
halcyon settings set graphics.blurQuality low
halcyon settings set glass.preset clear
halcyon settings set graphics.lowPowerGraphics true
```

**Two power daemons.** `halcyon doctor` names them. Disable one:

```sh
systemctl disable --now tlp
```

**The assistant does not answer.**

```sh
halcyon assistant status        # which backend, and why
journalctl --user -u halcyon-assistant -n 50
```

**NVIDIA.** GPU variables are only set when the proprietary driver is
loaded. If you have just installed it, re-run `./install.sh
--config-only` so detection runs again.

**Fractional scaling looks blurry.** Set the scale per monitor in
`displays.monitors` rather than globally; Halcyon does not force
`Text.NativeRendering`, which is what causes blurry text at fractional
scales.

---

## Uninstalling and restoring

```sh
./uninstall.sh --dry-run    # see what would be removed
./uninstall.sh
```

Removes Halcyon's files, disables its services, and **restores your
pre-Halcyon configuration from the newest backup** — so uninstalling
puts the machine back, rather than just leaving a hole. Your own files,
including `~/.config/hypr/local.lua`, are left alone either way. It does
not remove packages it installed; it tells you which ones they were.

| Flag | Effect |
|---|---|
| `-n`, `--dry-run` | Show what would be removed. |
| `-y`, `--yes` | Do not prompt. |
| `--keep-config` | Keep `~/.config/halcyon` — settings and generated files. |
| `--no-restore` | Remove Halcyon without restoring what it replaced. |
| `--purge` | Also delete the backups. Cannot be undone. |

To go back to a specific install without uninstalling:

```sh
./restore.sh --list                 # every backup, with its timestamp
./restore.sh --show latest          # what that backup contains
./restore.sh latest
./restore.sh 2026-01-15T09-31-02
```

The manifest records both files that were replaced and paths that did
not exist before, so a restore removes what Halcyon added instead of
leaving orphans behind. `--dry-run` works here too.

---

## Extending Halcyon

### A new AI provider

Add a module to `src/halcyon/assistant/providers/` with a class exposing
`available()`, `ask(text, context)` yielding events, and `status()`.
Register it in `providers/__init__.py` and add its name to the
`assistant.provider` enum in `settings.default.json`. It appears in
Settings automatically. `providers/local.py` is the reference: intent
parsing, tool calls, streaming.

### A new search provider

Write a function `(query, settings, limit) -> list[Result]` in
`src/halcyon/search/providers.py` and add it to `REGISTRY`. It gets a
time budget and is isolated — if it raises, the rest of the search still
returns. Add a default to `search.providers` so it can be switched off.

### A new widget

Add a QML file under `config/quickshell/halcyon/Modules/`, build it on
`GlassSurface` so it inherits the material, and read from `Theme` rather
than hard-coding colours or durations. Register it in `shell.qml`. If it
should be toggleable, add a setting and a keybind to the catalog.

### A new desktop action

Add an `Action` to `src/halcyon/actions.py` with typed `Param`s. It
becomes available to the assistant, to Spotlight, and to `halcyon
action` at once. Mark it `destructive=True` if it should ask first, and
`requires_setting=` if it should be gated.

### A new preset

Drop a JSON file in `themes/`. See [Presets](#presets).

---

## Development

```sh
./scripts/dev/validate.sh
```

Runs everything: `shellcheck` over 25 scripts, executable-bit checks,
Lua parsing, QML parsing across 78 files, Python compilation, 128 unit
tests, `pyright`, JSON and JSONC schema checks, a full theme generation
validated against Hyprland's option table, systemd unit parsing, and
cross-file consistency (every role present in every package map, no
duplicate shortcuts, the default bar layout resolves).

```sh
PYTHONPATH=src python3 -m unittest discover -t . -s tests
./scripts/dev/check-hypr-config.py      # parse the Hyprland config without Hyprland
```

`scripts/dev/hypr-config-probe.lua` loads the real configuration against
a stand-in `hl` table, so the whole thing — options, binds, animations,
window/layer/workspace rules — can be checked on a machine where
Hyprland is not running.

---

## Licence

MIT. See [LICENSE](LICENSE).

Halcyon is an original work. It is inspired by Apple's design language;
it contains none of Apple's assets, icons, fonts or code. The default
typeface is Inter, an open font chosen for its similar feel. Icon
glyphs come from Nerd Fonts' Material Design set.
