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

Upstream's bindings are all still there. For example, `Super + Q` closes
a window, `Super + Enter` opens a terminal, and `Super` on its own opens
search.

### Hypr mode: a second set of keybinds

Hypr mode gives you a second layer, so the same chords can do something
else. Press `Super + F10 + H` (a function key, Super and a letter, held
together) to turn it on, and press `Escape` to turn it off. The same key
turns it off too. A notification says when the mode starts and ends.

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
