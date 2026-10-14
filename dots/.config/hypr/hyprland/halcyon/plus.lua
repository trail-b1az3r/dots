-- hyprland-plus: the Halcyon fork's window types, Plus Tiles and drag options, set up for this desktop.
--
-- The per-app preferences (which apps are Plus Tiles, float, keep their size, and so on) are in app_rules.lua,
-- applied by rules.lua. They work on stock Hyprland too; the Plus-only ones are then skipped.
--
-- The drag options (binds:drag_keep_grab_point and binds:drag_guide) are on by default in the fork, so they
-- are not set here. Set them to false in ~/.config/hypr/custom if you want upstream's drag behaviour.

local caps = require("hyprland.halcyon.compositor")

if caps.strips then
    -- Superposition strip at the right edge, 12% of the screen wide. It overlays the tiles (reserve = false).
    hl.config({ superposition = { edge = 1, size = 0.12, reserve = false } })
end

if caps.tiles then
    -- Plus Tiles. These are the defaults, written out so they are easy to find and change in
    -- ~/.config/hypr/custom (anything set there wins).
    hl.config({
        plus = {
            enabled = true,
            all_tiled = false,          -- true: every tiled window is a Plus Tile, not only the plus apps
            edit_submap = "plus-edit",  -- defined in tiles.lua
            edit_preview = true,        -- preview edge moves, apply on Enter
            step = 40,
            step_fine = 10,
            step_coarse = 160,
            min_width = 120,
            min_height = 90,
            auto_restore = true,        -- keep custom sizes when windows open, close or move
            focus_preview = false,
            feedback = {
                border_size = 3,
                fill_opacity = 0.22,
                duration = 450,
                rounding = 8,
            },
        },
    })
end

-- Per-app rules
local function loadAppRules()
    local userFile = HOME .. "/.config/hypr/custom/app_rules.lua"
    if is_file_exists(userFile) then
        return dofile(userFile)
    end
    return require("hyprland.halcyon.app_rules")
end

require("hyprland.halcyon.rules").apply(loadAppRules(), caps)
