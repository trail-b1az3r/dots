-- Smart window rules: what each app should do, in one place. Edit this file to change them. Hyprland reloads
-- when you save.
--
-- To keep your own version through Halcyon updates, copy this file to ~/.config/hypr/custom/app_rules.lua and
-- edit the copy. It is used instead of this one.
--
-- Each entry matches windows by class (and optionally title), as Lua patterns in Hyprland's regex syntax, and
-- sets any of these. rules.lua turns them into window rules and reports anything it does not understand.
--
--  Native Hyprland rules (work on any Hyprland):
--    workspace = 2 or "special:music"   open on that workspace
--    float = true / tile = true         start floating, or tiled
--    min_size = { 400, 300 }            smallest size, in pixels
--    max_size = { 1600, 1000 }          largest size, in pixels
--    title_bar = false                  no border, shadow or other decoration (Hyprland's decorate rule;
--                                       Hyprland has no title bars of its own)
--    center = true                      centred when it opens floating
--    monitor = "DP-1"                   open on that monitor
--
--  Plus rules (hyprland-plus only; skipped with a warning on stock Hyprland):
--    plus = true                        a Plus Tile: ordinary until Move Edge is used on it
--    keep_size = true                   Fit to Neighbors and auto-restore leave its size alone (plus_locked)
--    superposition = true               kept on the screen-edge strip, above fullscreen windows
--
--  Shorthand:
--    role = "tile" | "float" | "plus" | "pinned"
--        tile: tiled. float: floating and centred. plus: a Plus Tile. pinned: floating, centred, on every workspace.

return {
    -- Terminals are Plus Tiles: they can be given custom sizes with Move Edge.
    { class = "^(kitty|foot|Alacritty|org.wezfurlong.wezterm|com.mitchellh.ghostty)$", role = "plus" },

    -- The music player stays on the screen-edge strip, visible over fullscreen windows.
    { class = "^([Ss]potify)$", superposition = true },

    -- Small utilities float, centred, with a sensible minimum size.
    { class = "^(org.gnome.Calculator|gnome-calculator|qalculate-gtk)$", role = "float", min_size = { 320, 460 } },
    { class = "^(pavucontrol|org.pulseaudio.pavucontrol|blueman-manager|nm-connection-editor)$", role = "float", min_size = { 560, 420 } },
}
