# Keybinds

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
| `Super + Shift + H` | HyperNix (if installed) |
| `Super + Alt + E` | Plus Tiles: Move Edge (see below) |
| `Super + Ctrl + F` | Plus Tiles: Fit to neighbours |
| `Super + Ctrl + Shift + F` | Plus Tiles: back to an ordinary tile |
| `Super + Ctrl + I` | Plus Tiles: geometry inspector |
| `Super + Alt + arrow` | Plus Tiles: move that edge out at once (`Shift`: in) |
| `Super + F10 + H` or `Super + Ctrl + H` | Hypr mode on and off |

Upstream's bindings are all still there. For example, `Super + Q` closes
a window, `Super + Enter` opens a terminal, and `Super` on its own opens
search.

`Super` on its own opens the overview when you let go of it, and only then: a
key pressed while `Super` is held (`Super + /`, for example) cancels that.
Every bind that holds `Super` gets a hidden companion that sends the cancel
(`halcyon/super_tap.lua`). An earlier version used one catch-all bind instead,
which also caught the `Super` key itself and stopped the overview opening.

The cheat sheet (`Super + /`) shows function keys as icons. Hover a line to
see its chord pressed, key by key, and released; click a key to press it.

### Plus Tiles

A Plus Tile is a tiled window that can be given a custom size. Until you use
Move Edge on it, it is an ordinary tile: the layout places and sizes it like
any other. Terminals are Plus Tiles (see `app_rules.lua`).

| In Move Edge (`Super + Alt + E`) | |
|---|---|
| arrows, or `H` `J` `K` `L` | select the left, bottom, top or right edge |
| `=` and `-` | move the edge out or in (`Shift`: a big step, `Ctrl`: a small one) |
| `Enter` | apply what the preview shows |
| `Escape` | cancel |
| `F` / `R` | fit to neighbours / back to an ordinary tile |

Moving an edge goes through the layout, so the tiles that share that edge give
up or take the space, and the board stays aligned. After that the tile is
*edge-modified*: Fit to Neighbors keeps its size and makes the neighbours fit
around it, and its size comes back after windows open, close or move. On an
ordinary tile, Fit to Neighbors just fits the layout's space.

The keys are in `halcyon/plus_keys.lua`, and the settings (steps, minimum sizes,
preview colours) in `halcyon/plus.lua`. Copy `plus_keys.lua` to
`~/.config/hypr/custom/plus_keys.lua` to change the keys: your copy is used
instead, and updates never overwrite it. `hyprctl plus inspect` prints the
focused tile's geometry, neighbours and limits.

### App rules

`halcyon/app_rules.lua` lists what each app should do: its workspace, floating
or tiled, minimum size, decorations, and the Plus settings (Plus Tile, keep its
size, superposition strip). Native Hyprland rules and the Plus-only ones are
marked in the file. Copy it to `~/.config/hypr/custom/app_rules.lua` to make it
yours. Mistakes are reported in one notification, and the rest still applies.

### Checking the configuration

```sh
halcyon config-check          # what is wrong, and how to fix it
halcyon config-check --fix    # also fix file permissions, after a backup
```

It reports Hyprland's own config errors, Plus options without hyprland-plus,
Lua that does not parse, malformed chords, two binds on one chord, repeated
lines in your custom files, missing plugins, Plus settings that contradict each
other, and wrong file permissions. It never rewrites your configuration.

### Hypr mode: a second set of keybinds

Hypr mode gives you a second layer, so the same chords can do something
else. Press `Super + Ctrl + H`, or `Super + F10 + H` (F10 before H; on many
laptops F10 also needs Fn), to turn it on, and `Escape` to turn it off. The
same keys turn it off too. A band of light swipes across the screen, then
the mode's binds appear and stay until the mode ends.

While the mode is on, the normal binds are off, so every chord in the mode
only has to be unique inside it. In the default set the arrow keys move the
focused window, where they normally change focus.

Change the keys and binds in `~/.config/hypr/hyprland/halcyon/hypr_mode.lua`.
It is a plain list: `toggle`, `exit`, and `binds` as
`{ chord, dispatcher, description }`, the same chord syntax and dispatchers as
`hl.bind`. Save the file and Hyprland reloads it.

Halcyon updates overwrite that file. To keep your own version, copy it to
`~/.config/hypr/custom/hypr_mode.lua` and edit the copy. Hyprland uses the
copy when it exists, and updates never touch it.
