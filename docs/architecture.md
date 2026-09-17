# Architecture

Halcyon is four layers that mostly do not know about each other:

```
       settings.json + wallpaper
                  │
        ┌─────────▼──────────┐
        │   Python core      │   palette → tokens → renderers
        │   src/halcyon/     │   actions, search, power, assistant
        └─────────┬──────────┘
                  │  generated files
     ┌────────────┼────────────┬──────────────┐
     ▼            ▼            ▼              ▼
 Hyprland     Quickshell     Waybar      hyprlock /
 (Lua)        (QML)          (JSONC+CSS)  hypridle
```

The core writes files. The three consumers read them. Nothing reads
another consumer's state, and nothing but the core writes generated
files.

## The generation pipeline

```
settings.json  ──┐
wallpaper      ──┼──▶  palette  ──▶  tokens  ──┬──▶  hypr-theme.lua
defaults       ──┘     palette.py    theme.py  ├──▶  hypr-runtime.lua
                                               ├──▶  hypr-keybinds.lua
                                               ├──▶  waybar-config.jsonc
                                               ├──▶  waybar-colors.css
                                               ├──▶  theme.json
                                               ├──▶  hyprlock-colors.conf
                                               └──▶  hypridle-timeouts.conf
```

`pipeline.apply()` runs the whole chain and then reloads whatever is
running. It is the only entry point that changes how the desktop looks.

**Settings** (`settings.py`) are your overrides deep-merged over
`config/system/settings.default.json`. Only overrides are written, and
every value is type-checked on the way in. A settings file written by a
newer schema version is refused rather than half-understood.

**Palette** (`palette.py`) extracts swatches from the wallpaper —
ImageMagick's histogram if it is installed, otherwise a pure-Python PNG
decoder that does its own unfiltering — and scores them by chroma, area
and mid-tone preference. A wallpaper-derived accent is clamped into a
band that works on both light and dark glass. An accent you chose by
hand is used exactly as you chose it.

**Tokens** (`theme.py`) turn settings plus a palette into one document:
colour ramps, glass parameters per elevation, type scale, spacing,
durations and curves. Accessibility floors are applied here, once, so
every renderer inherits them.

**Renderers** (`render.py`) project that document into each consumer's
own syntax. They share nothing but the token document — which is why a
colour cannot be right in Waybar and wrong in Quickshell.

**Validation happens before writing.** `render_hypr_runtime_lua` checks
every option it is about to emit against Hyprland's own option table
(`hyprctl descriptions -j` when the compositor is running, the shipped
snapshot when it is not) and raises rather than write a config Hyprland
would reject. The keybind renderer refuses to emit two binds for the
same chord. Files are written atomically, so a crash mid-write cannot
leave a half-file that Hyprland then fails to parse.

## Hyprland

`~/.config/hypr/hyprland.lua` requires four modules and then your own
`local.lua` through `pcall`:

| File | What it holds |
|---|---|
| `halcyon/generated.lua` | Loads the generated files; installs emergency bindings if they fail. |
| `halcyon/appearance.lua` | Everything visual that is not generated. |
| `halcyon/behaviour.lua` | Window rules, gestures, layout behaviour. |
| `halcyon/autostart.lua` | The session: shell, bar, portals, agents. |
| `local.lua` | Yours. Loaded last, never overwritten, never backed up over. |

Hyprland 0.56 scopes errors per `require()`, so a typo in one file does
not take the others down. `generated.lua` goes further: if the generated
files are missing or broken it binds `Super + Return`, `Super + W` and
`Super + Ctrl + Escape` and raises a notification — enough of a desktop
to fix the problem from.

## Quickshell

```
config/quickshell/halcyon/
├── shell.qml          ShellRoot, 15 IPC handlers
├── Config/            Paths, Config, Theme  (singletons)
├── Services/          13 singletons wrapping system state
├── Components/        16 reusable pieces, GlassSurface among them
└── Modules/           the surfaces: Spotlight, ControlCenter, …
```

`Theme` is a singleton that watches `theme.json` with a `FileView` and
`watchChanges`. When the core regenerates it, every binding that reads
`Theme` updates — there is no reload step and no polling.

Services wrap `Quickshell.Services.*` (Pipewire, Mpris, UPower,
Notifications, SystemTray, Pam, Polkit) and Halcyon's own CLI, so a
module never shells out directly.

`GlassSurface` is the material. It layers a tint, a specular highlight
along the top edge, an inner shadow, a hairline border and a `MultiEffect`
drop shadow over the compositor's blur, with the layer's blur configured
through `layerrule`. Elevation picks the parameters; a module sets an
elevation, not a colour.

## Waybar

Waybar is GTK3, which means no CSS custom properties and no
`backdrop-filter`. The generated stylesheet uses `@define-color` only,
and the generator checks that every colour used is defined.

Module definitions live in `config/waybar/modules.jsonc`; the layout
comes from `bar.left`/`center`/`right`. Halcyon's own modules are
signal-driven (`SIGRTMIN+N`) rather than polled — the core sends the
signal when something changes, which is why the bar costs almost nothing
when the machine is idle.

## The action layer

`actions.py` holds 33 registered actions. Each declares typed `Param`s
with optional choices, ranges and patterns. `validate()` coerces and
range-checks, rejects undeclared parameters, and confines `path`
parameters to your home directory and mounted volumes.

Nothing in this layer uses `shell=True`. Destructive actions require
`confirmed=True`. An action can be gated on a setting — `web.search` is
gated on `assistant.privacy.allowWebAccess`, which is off by default.

Everything that acts on the desktop goes through here: the assistant,
Spotlight, the CLI, and the shell's IPC. One allowlist, one validator.

## The assistant

```
microphone ──▶ audio.py ──▶ stt.py ──▶ intents.py ──┬─▶ actions.py
                                                    └─▶ llm.py ──▶ actions.py
                                                             │
                                                        tts.py ──▶ speaker
```

`daemon.py` is a threading Unix server on
`$XDG_RUNTIME_DIR/halcyon-assistant.sock`, mode 0600, speaking NDJSON.
Operations: `ask`, `listen`, `cancel`, `confirm`, `subscribe`, `status`,
`providers`, `history`, `clear`.

Backends live in `assistant/providers/`. Each exposes `available()`,
`ask()` and `status()`; the daemon picks per request. `nixorb.py` is a
real adapter over NixOrb's socket with a CLI fallback. `local.py` runs
intents, then the model, then tool calls.

Deterministic rules run before any model. If a rule matches, the action
executes and no model runs at all.

## Services

Ten systemd user units, all `PartOf=halcyon-session.target`, so the
session starts and stops as a unit:

`halcyon-shell`, `halcyon-bar`, `halcyon-wallpaper`, `halcyon-idle`,
`halcyon-polkit`, `halcyon-power`, `halcyon-assistant`,
`halcyon-clipboard`, `halcyon-clipboard-image`.

## Degradation

Every external dependency is optional and every call site says what
happens without it. `shell.call_or_fallback()` routes Spotlight, the
power menu, network and audio to a dmenu-style picker when Quickshell is
not running. `palette.py` falls back to a built-in PNG decoder without
ImageMagick. `tts.py` falls back from Piper to `espeak-ng`. `power.py`
reports `none` rather than driving a backend that is not there.

The rule throughout: a missing optional dependency degrades one feature,
never the desktop.
