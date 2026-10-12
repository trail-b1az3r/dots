-- Plustile windows: a tiled window that can be resized from each of its four edges.
--
-- Only windows that have the plustile rule can be resized this way. Enable it per app, for example:
--   hl.window_rule({ match = { class = "^(kitty)$" }, plustile = true })
--
--   SUPER + ALT + Left / Right / Up / Down           move that edge outwards: the tile grows, its neighbours give up space
--   SUPER + ALT + SHIFT + Left / Right / Up / Down   move that edge inwards: the tile shrinks
--
-- Each press moves the edge by STEP pixels. Only the edge you press moves, so a tile never
-- changes size on its other sides. Windows without the plustile rule are left alone.

-- Needs the Halcyon Hyprland fork (hl.dsp.window.resize_edge). On stock Hyprland this file does nothing.
if hl.dsp and hl.dsp.window and hl.dsp.window.resize_edge then
    local STEP = 40

    local edges = {
        { key = "Left",  edge = "left" },
        { key = "Right", edge = "right" },
        { key = "Up",    edge = "top" },
        { key = "Down",  edge = "bottom" },
    }

    -- Fit: the focused plustile window takes the free space around it, from its neighbours.
    hl.bind("SUPER + CTRL + F", hl.dsp.window.fit_plustile(), { description = "Plustile: Fit to neighbours" })

    for _, e in ipairs(edges) do
        hl.bind("SUPER + ALT + " .. e.key, hl.dsp.window.resize_edge({ edge = e.edge, amount = STEP }),
            { description = "Plustile: Grow the " .. e.edge .. " edge" })
        hl.bind("SUPER + ALT + SHIFT + " .. e.key, hl.dsp.window.resize_edge({ edge = e.edge, amount = -STEP }),
            { description = "Plustile: Shrink the " .. e.edge .. " edge" })
    end
end
