-- Plus Tiles keys. Edit this file to change them. Hyprland reloads when you save.
--
-- To keep your own version through Halcyon updates, copy this file to
-- ~/.config/hypr/custom/plus_keys.lua and edit that copy. It is used instead of this one, so updates never
-- overwrite your keys.
--
-- A Plus Tile is an ordinary tiled window until you use Move Edge on it. Which windows are Plus Tiles is set in
-- plus.lua (the plustile rule, or plus:all_tiled). The other Plus settings (steps, minimum sizes, colours) are
-- plus:* options, also in plus.lua.

return {
    -- Move Edge: start editing the focused Plus Tile's edges, or commit if already editing.
    move_edge = "SUPER + ALT + E",

    -- Fit to Neighbors. An ordinary tile fits the layout's space. An edge-modified tile keeps its size and the
    -- neighbours fit around it.
    fit = "SUPER + CTRL + F",

    -- Back to an ordinary tile, at the size it had before its first edge move.
    reset = "SUPER + CTRL + SHIFT + F",

    -- Geometry inspector: outlines the board, and shows the focused tile's neighbours and limits.
    inspect = "SUPER + CTRL + I",

    -- Move an edge at once, without the edit mode: these modifiers plus an arrow key, by quick_step pixels.
    quick_grow = "SUPER + ALT",
    quick_shrink = "SUPER + ALT + SHIFT",
    quick_step = 40,

    -- true: SUPER + arrows move focus by real tile geometry (the nearest tile that way) instead of the layout's
    -- movefocus. It replaces upstream's SUPER + arrow binds, so it is off unless you turn it on.
    geometric_focus = false,

    -- Keys while editing (the "plus-edit" submap, plus:edit_submap). Only these work until you commit or cancel.
    edit = {
        -- select an edge
        select = {
            Left = "left", Right = "right", Up = "top", Down = "bottom",
            H = "left", L = "right", K = "top", J = "bottom",
        },
        -- move the selected edge out (the tile grows) or in (it shrinks)
        grow = "Equal",
        shrink = "Minus",
        -- held with grow or shrink: a fine (plus:step_fine) or coarse (plus:step_coarse) step
        fine = "CTRL",
        coarse = "SHIFT",
        commit = "Return",
        cancel = "Escape",
        fit = "F",
        reset = "R",
    },
}
