# Keyboard shortcuts

Every binding is defined in `config/system/keybinds.catalog.json` and
can be overridden individually. Press `Ctrl + /` for this list on
screen.

## Design

This is a Linux-native layout, not a copy of anyone's.

It borrows the macOS **capture** shortcuts — `Super+Shift+3/4/5` — because
that muscle memory is genuinely good and nothing else wants those chords.

That has one consequence worth knowing: `Super+Shift+<digit>` is
therefore **not** move-to-workspace. Move-to-workspace is
`Super+Ctrl+<digit>`. Splitting the digits across two modifiers would
have been worse than moving all of them.

Beyond that: `Super` alone switches or focuses, `Super+Shift` moves,
`Super+Alt` resizes, `Super+Ctrl` is for workspace and session
operations.

> **A note on `Ctrl + /` and `Ctrl + Shift + S`.** These are compositor-level
> binds, so they are taken before the focused application sees them —
> `Ctrl + Shift + S` will shadow "Save As" in GIMP and Inkscape, and
> `Ctrl + /` will shadow "toggle comment" in most editors. Both keep their
> `Super` equivalents (`Super + /`, `Super + Shift + 4`), so if an
> application needs its chord back:
>
> ```sh
> halcyon settings set keybinds.shot.region none
> halcyon settings set keybinds.keybindHelp none
> halcyon theme apply
> ```

## System

| Shortcut | Action |
|---|---|
| `Super + Space` | Spotlight search |
| `Super + Shift + Space` | Ask the assistant |
| `Super + A` | Assistant push-to-talk |
| `Super + Shift + A` | Cancel the assistant |
| `Super + C` | Control Center |
| `Super + N` | Notification centre |
| `Super + E` | Mission Control overview |
| `Super + Tab` | Application switcher |
| `Super + Shift + Tab` | Application switcher, backwards |
| `Super + K` | Calendar |
| `Super + D` | Desktop widgets |
| `Super + V` | Clipboard history |
| `Super + ,` | Settings |
| `Ctrl + /` | This list (also `Super + /`) |
| `Super + Escape` | Power menu |
| `Super + Ctrl + Q` | Lock the screen |
| `Super + Ctrl + R` | Reload the desktop |
| `Super + Ctrl + Escape` | Log out |
| `Super + Shift + T` | Toggle light / dark |
| `Super + Shift + N` | Toggle Do Not Disturb |
| `Super + Shift + W` | Next wallpaper |
| `Super + Shift + P` | Cycle power profile |

## Windows

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
| `Super + ← → ↑ ↓` | Focus in that direction |
| `Super + Shift + ← → ↑ ↓` | Move the window |
| `Super + Alt + ← → ↑ ↓` | Resize |

## Workspaces

| Shortcut | Action |
|---|---|
| `Super + 1 … 0` | Switch to workspace |
| `Super + Ctrl + 1 … 0` | Move window to workspace |
| `Super + Ctrl + →` | Next workspace |
| `Super + Ctrl + ←` | Previous workspace |
| `Super + \`` | Back and forth |
| `Super + S` | Scratchpad |
| `Super + Shift + S` | Move window to scratchpad |
| `Super + Ctrl + ↑` | Focus next monitor |
| `Super + Ctrl + ↓` | Focus previous monitor |
| `Super + Shift + scroll` | Next / previous workspace |

## Capture

| Shortcut | Action |
|---|---|
| `Super + Shift + 3` | Screenshot the screen |
| `Ctrl + Shift + S` | Screenshot a region (also `Super + Shift + 4`) |
| `Super + Shift + 5` | Screenshot & recording panel |
| `Super + Shift + 6` | Screenshot the focused window |

Saved to `applications.screenshotDir` and `applications.recordingDir`.

## Media and hardware keys

| Key | Action |
|---|---|
| `XF86AudioRaiseVolume` / `LowerVolume` | Volume |
| `XF86AudioMute` | Mute output |
| `XF86AudioMicMute` | Mute microphone |
| `XF86MonBrightnessUp` / `Down` | Brightness |
| `XF86AudioPlay` | Play / pause |
| `XF86AudioNext` / `Prev` | Track |

## Applications

| Shortcut | Action |
|---|---|
| `Super + Return` | Terminal |
| `Super + Shift + Return` | File manager |
| `Super + B` | Browser |
| `Super + Shift + H` | HyperNix |

Which applications these open comes from the `applications` settings.

## Rebinding

Each binding has an ID. `halcyon settings set keybinds.<id> "<chord>"`:

```sh
halcyon settings set keybinds.spotlight "SUPER + P"
halcyon settings set keybinds.window.close "ALT + F4"
halcyon settings set keybinds.overview none      # unbind
halcyon settings unset keybinds.spotlight        # back to the default
halcyon theme apply
```

IDs are in `config/system/keybinds.catalog.json` — the `id` field of
each entry.

### Collisions

The generator refuses to emit two bindings for the same chord. The
first one wins and the generated file carries a comment naming which one
was dropped:

```lua
-- skipped overview: SUPER + P is already bound to spotlight
```

If a binding you set does not work, look there first.

### Emergency bindings

If the generated files fail to load, `config/hypr/halcyon/generated.lua`
binds `Super + Return` (terminal), `Super + W` (close window) and
`Super + Ctrl + Escape` (log out), and raises a notification. You are
never left at a black screen with no way in.
