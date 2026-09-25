-- Halcyon look: a little more air between windows, softer corners and a
-- deeper blur behind the shell's glass panels. Only keys that differ
-- from hyprland/general.lua are set here.
--
-- Border colours are deliberately not set: they come from the wallpaper
-- (hyprland/colors.lua, written by matugen) or from the active theme.

hl.config({
    general = {
        gaps_in = 5,
        gaps_out = 10,

        snap = {
            window_gap = 5,
            monitor_gap = 10
        }
    },
    decoration = {
        rounding = 20,

        blur = {
            size = 12,
            passes = 4,
            vibrancy = 0.6,
            -- Blur behind popups too, so menus read as the same glass as
            -- the panels they open from.
            popups = true
        },
        shadow = {
            range = 28,
            offset = {0, 4},
            color = "rgba(0000002E)"
        }
    }
})
