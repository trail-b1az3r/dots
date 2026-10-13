-- Plus Tiles: tiled windows that can be given intentionally unequal sizes.
--
-- A Plus Tile behaves like every other tiled window until you use Move Edge on it:
--   SUPER + ALT + E      Move Edge: select an edge with the arrows (or H J K L), move it with = and -
--                        (SHIFT coarse, CTRL fine), see the preview, then Enter to apply or Escape to cancel.
--   SUPER + ALT + arrow  move that edge out at once (SHIFT: in)
--   SUPER + CTRL + F     Fit to Neighbors
--   SUPER + CTRL + SHIFT + F   back to an ordinary tile
--   SUPER + CTRL + I     geometry inspector
-- The keys are in plus_keys.lua (or your copy in ~/.config/hypr/custom/plus_keys.lua).
--
-- Moving an edge goes through the layout, so the tiles sharing that boundary give up or take the space. Once an
-- edge has been moved, the tile keeps its custom size when windows open, close or move (plus:auto_restore).

-- Needs the Halcyon Hyprland fork (hl.dsp.plus). On stock Hyprland this file does nothing.
if not (hl.dsp and hl.dsp.plus) then
    return
end

local function loadKeys()
    local userFile = HOME .. "/.config/hypr/custom/plus_keys.lua"
    if is_file_exists(userFile) then
        return dofile(userFile)
    end
    return require("hyprland.halcyon.plus_keys")
end

local K = loadKeys()
local E = K.edit or {}

local function bind(chord, dispatcher, description)
    if chord and chord ~= "" then
        hl.bind(chord, dispatcher, { description = description })
    end
end

bind(K.move_edge, hl.dsp.plus.edit({ action = "toggle" }), "Plus: Move edge (edit the focused tile's edges)")
bind(K.fit, hl.dsp.plus.fit(), "Plus: Fit to neighbours")
bind(K.reset, hl.dsp.plus.reset(), "Plus: Back to an ordinary tile")
bind(K.inspect, hl.dsp.plus.inspect(), "Plus: Geometry inspector")

local ARROWS = {
    { key = "Left", edge = "left", dir = "left" },
    { key = "Right", edge = "right", dir = "right" },
    { key = "Up", edge = "top", dir = "up" },
    { key = "Down", edge = "bottom", dir = "down" },
}

-- Quick edge moves, outside the edit mode, by quick_step pixels. They count as Move Edge: the tile becomes
-- edge-modified and keeps its new size.
local STEP = K.quick_step or 40
for _, a in ipairs(ARROWS) do
    if K.quick_grow and K.quick_grow ~= "" then
        bind(K.quick_grow .. " + " .. a.key, hl.dsp.window.resize_edge({ edge = a.edge, amount = STEP }), "Plus: Move the " .. a.edge .. " edge out")
    end
    if K.quick_shrink and K.quick_shrink ~= "" then
        bind(K.quick_shrink .. " + " .. a.key, hl.dsp.window.resize_edge({ edge = a.edge, amount = -STEP }), "Plus: Move the " .. a.edge .. " edge in")
    end
end

-- Geometric focus, only if asked for: it replaces upstream's SUPER + arrow binds.
if K.geometric_focus then
    for _, a in ipairs(ARROWS) do
        hl.unbind("SUPER + " .. a.key)
        bind("SUPER + " .. a.key, hl.dsp.plus.focus({ direction = a.dir }), "Plus: Focus the tile " .. a.dir)
    end
end

-- The edit mode's keys. The compositor switches to this submap when editing starts (plus:edit_submap), and back
-- when it ends, also if focus or the workspace changes.
hl.define_submap("plus-edit", function()
    for key, edge in pairs(E.select or {}) do
        hl.bind(key, hl.dsp.plus.select_edge({ edge = edge }), { description = "Plus edit: Select the " .. edge .. " edge" })
    end
    if E.grow then
        hl.bind(E.grow, hl.dsp.plus.move_edge({ direction = "out" }), { description = "Plus edit: Move the edge out" })
        if E.coarse then hl.bind(E.coarse .. " + " .. E.grow, hl.dsp.plus.move_edge({ direction = "out", step = "coarse" })) end
        if E.fine then hl.bind(E.fine .. " + " .. E.grow, hl.dsp.plus.move_edge({ direction = "out", step = "fine" })) end
    end
    if E.shrink then
        hl.bind(E.shrink, hl.dsp.plus.move_edge({ direction = "in" }), { description = "Plus edit: Move the edge in" })
        if E.coarse then hl.bind(E.coarse .. " + " .. E.shrink, hl.dsp.plus.move_edge({ direction = "in", step = "coarse" })) end
        if E.fine then hl.bind(E.fine .. " + " .. E.shrink, hl.dsp.plus.move_edge({ direction = "in", step = "fine" })) end
    end
    if E.commit then hl.bind(E.commit, hl.dsp.plus.commit(), { description = "Plus edit: Apply" }) end
    if E.cancel then hl.bind(E.cancel, hl.dsp.plus.cancel(), { description = "Plus edit: Cancel" }) end
    if E.fit then hl.bind(E.fit, hl.dsp.plus.fit(), { description = "Plus edit: Fit to neighbours" }) end
    if E.reset then hl.bind(E.reset, hl.dsp.plus.reset(), { description = "Plus edit: Back to an ordinary tile" }) end
end)
