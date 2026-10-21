-- Halcyon's own window layouts, for Settings > Interface > Windows (halcyon-theme placement):
--
--   stacked        two windows at a time, one above the other. A third opens on the next empty workspace.
--   side-by-side   two windows at a time, next to each other. A third opens on the next empty workspace.
--   mondrian       a Mondrian grid: each new window splits the biggest tile, at a ratio from a fixed sequence,
--                  the other way from the cut before, so the tiles come out as interlocking, uneven blocks.
--   golden-plus    a golden spiral that holds many windows: the first window takes 61.8 % of the screen, the next
--                  61.8 % of what is left, turning round the spiral (left, top, right, bottom). It turns only as
--                  often as keeps every window usable; the windows after the last turn share the rest as a grid.
--
-- Golden ratio and cursor position are Hyprland's own dwindle layout (placement.lua sets those), and so is golden
-- ratio plus when it is set to use dwindle (golden-plus-dwindle). These four
-- are layouts written in Lua (hl.layout.register): Hyprland hands recalculate() the work area and the tiled
-- windows, and each window is placed with target.place(box). Gaps and borders are added by Hyprland itself.
-- Floating windows are not part of any of them.
--
-- The box maths are plain functions on {x, y, w, h} tables, so they run (and are tested) without Hyprland.

local M = {}

M.NAMES = { stacked = "halcyon-stacked", ["side-by-side"] = "halcyon-side-by-side", mondrian = "halcyon-mondrian",
            ["golden-plus"] = "halcyon-golden-plus" }

M.PHI = 0.6180339887
-- The spiral stops before a window would be narrower than this (in pixels), or after this many turns: from there
-- the windows still to come share the rest as a grid, so no window ends up a sliver.
M.GOLDEN_MIN = 320
M.GOLDEN_TURNS = 6

-- The ratios Mondrian splits at, in turn: never a plain half twice in a row, never thinner than about a third.
M.MONDRIAN_RATIOS = { 0.62, 0.5, 0.4, 0.58, 0.45, 0.66, 0.38, 0.55 }

-- n boxes in a row (side by side) or a column (stacked), equal, filling area.
function M.even(area, n, across)
    local boxes = {}
    for i = 1, n do
        if across then
            local w = area.w / n
            boxes[i] = { x = area.x + w * (i - 1), y = area.y, w = w, h = area.h }
        else
            local h = area.h / n
            boxes[i] = { x = area.x, y = area.y + h * (i - 1), w = area.w, h = h }
        end
    end
    return boxes
end

function M.stacked(area, n)
    return M.even(area, n, false)
end

function M.side_by_side(area, n)
    return M.even(area, n, true)
end

-- Mondrian: start with the whole area; every further window splits the biggest tile so far (the first of equals).
-- Each cut runs the other way from the cut that made the tile, so columns and rows interlock the way a Mondrian
-- painting's lines do, unless that would leave a sliver (thinner than about 1 : 3.5), when it runs the other way.
-- The earlier window keeps the first part and the new one gets the rest, so it opens beside the tile it came from.
local function cut(b, across, r)
    if across then
        return { x = b.x, y = b.y, w = b.w * r, h = b.h, cut = "across" },
            { x = b.x + b.w * r, y = b.y, w = b.w * (1 - r), h = b.h, cut = "across" }
    end
    return { x = b.x, y = b.y, w = b.w, h = b.h * r, cut = "down" },
        { x = b.x, y = b.y + b.h * r, w = b.w, h = b.h * (1 - r), cut = "down" }
end

local function sliver(a, b)
    local function thin(x)
        return math.min(x.w, x.h) / math.max(x.w, x.h) < 0.285
    end
    return thin(a) or thin(b)
end

function M.mondrian(area, n)
    local boxes = {}
    if n < 1 then
        return boxes
    end
    boxes[1] = { x = area.x, y = area.y, w = area.w, h = area.h }
    for i = 2, n do
        local k, best = 1, -1
        for j, b in ipairs(boxes) do
            local size = b.w * b.h
            if size > best + 1e-6 then
                k, best = j, size
            end
        end
        local b = boxes[k]
        local r = M.MONDRIAN_RATIOS[(i - 2) % #M.MONDRIAN_RATIOS + 1]
        local across
        if b.cut == "across" then
            across = false
        elseif b.cut == "down" then
            across = true
        else
            across = b.w >= b.h
        end
        local first, second = cut(b, across, r)
        if sliver(first, second) then
            first, second = cut(b, not across, r)
        end
        boxes[k] = first
        table.insert(boxes, k + 1, second)
    end
    -- Hand back plain boxes.
    for j, b in ipairs(boxes) do
        boxes[j] = { x = b.x, y = b.y, w = b.w, h = b.h }
    end
    return boxes
end

-- k boxes in a grid filling area: as many columns as keeps the cells closest to the area's own shape.
function M.grid(area, k)
    local boxes = {}
    if k < 1 then
        return boxes
    end
    local cols = math.max(1, math.floor(math.sqrt(k * area.w / math.max(area.h, 1)) + 0.5))
    cols = math.min(cols, k)
    local rows = math.ceil(k / cols)
    local i = 0
    for r = 1, rows do
        -- The last row takes what is left, spread across its width.
        local in_row = (r < rows) and cols or (k - cols * (rows - 1))
        local w = area.w / in_row
        local h = area.h / rows
        for c = 1, in_row do
            i = i + 1
            boxes[i] = { x = area.x + w * (c - 1), y = area.y + h * (r - 1), w = w, h = h }
        end
    end
    return boxes
end

-- The golden spiral with `turns` turns, then a grid of the windows left in what remains.
local function spiral(area, n, turns)
    local boxes = {}
    local rest = { x = area.x, y = area.y, w = area.w, h = area.h }
    local side = 0      -- 0: the window on the left of what is left, 1: top, 2: right, 3: bottom
    local i = 1
    while i <= n do
        local left = n - i + 1
        if left == 1 or i > turns then
            for j, b in ipairs(M.grid(rest, left)) do
                boxes[i + j - 1] = b
            end
            break
        end
        local across = (side % 2 == 0)
        local piece = (across and rest.w or rest.h) * M.PHI
        local after = (across and rest.w or rest.h) - piece
        if side == 0 then
            boxes[i] = { x = rest.x, y = rest.y, w = piece, h = rest.h }
            rest = { x = rest.x + piece, y = rest.y, w = after, h = rest.h }
        elseif side == 1 then
            boxes[i] = { x = rest.x, y = rest.y, w = rest.w, h = piece }
            rest = { x = rest.x, y = rest.y + piece, w = rest.w, h = after }
        elseif side == 2 then
            boxes[i] = { x = rest.x + after, y = rest.y, w = piece, h = rest.h }
            rest = { x = rest.x, y = rest.y, w = after, h = rest.h }
        else
            boxes[i] = { x = rest.x, y = rest.y + after, w = rest.w, h = piece }
            rest = { x = rest.x, y = rest.y, w = rest.w, h = after }
        end
        side = (side + 1) % 4
        i = i + 1
    end
    return boxes
end

local function smallest_side(boxes)
    local least = math.huge
    for _, b in ipairs(boxes) do
        least = math.min(least, b.w, b.h)
    end
    return least
end

-- The golden spiral, for any number of windows: as many turns as keep every window at least GOLDEN_MIN pixels
-- on its short side, the windows past the last turn sharing what is left as a grid. With many windows the spiral
-- has fewer turns, so they all stay usable; with none possible it is a plain grid.
function M.golden_plus(area, n)
    if n < 1 then
        return {}
    end
    for turns = math.min(n - 1, M.GOLDEN_TURNS), 1, -1 do
        local boxes = spiral(area, n, turns)
        if smallest_side(boxes) >= M.GOLDEN_MIN then
            return boxes
        end
    end
    return spiral(area, n, 0)
end

M.ARRANGE = { stacked = M.stacked, ["side-by-side"] = M.side_by_side, mondrian = M.mondrian,
              ["golden-plus"] = M.golden_plus }

-- How many windows the capped layouts hold on one workspace.
M.CAP = { stacked = 2, ["side-by-side"] = 2 }

-- The mode placement.lua chose (HALCYON_PLACEMENT), or nil for Hyprland's own dwindle modes.
function M.current()
    local mode = rawget(_G, "HALCYON_PLACEMENT")
    if mode and M.ARRANGE[mode] then
        return mode
    end
    return nil
end

-- Tiled, ordinary windows on a workspace: what a cap counts.
-- Windows are compared by address: every query hands back a new object for the same window.
function M.tiled_count(windows, except)
    local skip = except and except.address
    local count = 0
    for _, w in ipairs(windows or {}) do
        if (skip == nil or w.address ~= skip) and not w.floating and not w.fullscreen and not w.pinned then
            count = count + 1
        end
    end
    return count
end

-- Whether a window that just opened has to go elsewhere under the current mode.
function M.over_cap(mode, window, windows)
    local cap = M.CAP[mode]
    if not cap or not window or window.floating then
        return false
    end
    local ws = window.workspace
    if not ws or ws.special then
        return false
    end
    return M.tiled_count(windows, window) >= cap
end

-- ── Wiring into Hyprland ───────────────────────────────────────────────────────────────────────────────────────

if rawget(_G, "hl") and hl.layout and hl.layout.register then
    for mode, name in pairs(M.NAMES) do
        local arrange = M.ARRANGE[mode]
        hl.layout.register(name, {
            recalculate = function(ctx)
                local targets = ctx.targets
                local boxes = arrange(ctx.area, #targets)
                for i, target in ipairs(targets) do
                    target:place(boxes[i])
                end
            end,
        })
    end

    -- The caps: a third tiled window on a workspace goes to the next empty one on the same monitor, and you go
    -- with it. Floating windows and special workspaces are left alone.
    hl.on("window.open", function(window)
        local mode = M.current()
        if not mode or not M.CAP[mode] then
            return
        end
        local ws = window and window.workspace
        if not ws then
            return
        end
        local windows = hl.get_workspace_windows(ws) or {}
        if M.over_cap(mode, window, windows) then
            hl.dispatch(hl.dsp.window.move({ workspace = "emptynm", follow = true, window = window }))
        end
    end)
end

return M
