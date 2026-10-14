-- Halcyon's own window layouts, for Settings > Interface > Windows (halcyon-theme placement):
--
--   stacked        two windows at a time, one above the other. A third opens on the next empty workspace.
--   side-by-side   two windows at a time, next to each other. A third opens on the next empty workspace.
--   mondrian       a Mondrian grid: each new window splits the biggest tile, at a ratio from a fixed sequence,
--                  the other way from the cut before, so the tiles come out as interlocking, uneven blocks.
--
-- Golden ratio and cursor position are Hyprland's own dwindle layout (placement.lua sets those). These three
-- are layouts written in Lua (hl.layout.register): Hyprland hands recalculate() the work area and the tiled
-- windows, and each window is placed with target.place(box). Gaps and borders are added by Hyprland itself.
-- Floating windows are not part of any of them.
--
-- The box maths are plain functions on {x, y, w, h} tables, so they run (and are tested) without Hyprland.

local M = {}

M.NAMES = { stacked = "halcyon-stacked", ["side-by-side"] = "halcyon-side-by-side", mondrian = "halcyon-mondrian" }

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

M.ARRANGE = { stacked = M.stacked, ["side-by-side"] = M.side_by_side, mondrian = M.mondrian }

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
