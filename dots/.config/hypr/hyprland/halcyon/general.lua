-- Halcyon look: a little more air between windows, softer corners and a
-- deeper blur behind the shell's glass panels. Only keys that differ
-- from hyprland/general.lua are set here.

hl.config({
    general = {
        gaps_in = 5,
        gaps_out = 10,

        col = {
            -- Warm amber, to match the default wallpaper. The shell's
            -- wallpaper theming recolours this once a palette exists.
            active_border = "rgba(E8894A66)",
            inactive_border = "rgba(31313600)"
        },
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
