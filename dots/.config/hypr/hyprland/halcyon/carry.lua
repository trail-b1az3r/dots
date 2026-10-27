-- Carry a window to another workspace: hold SUPER, drag a window with the left button, and switch workspace with
-- the arrow keys (CTRL + SUPER + ←/→, or any other workspace key). The window comes along and stays under the cursor,
-- and you keep dragging it on the new workspace.
--
-- Hyprland has no "a drag is in progress" to ask for, so this watches the button: SUPER + left press notes the
-- window under the cursor, letting go of the left button (with or without SUPER still held) forgets it. Both binds
-- are non-consuming, so the drag itself (keybinds.lua: SUPER + mouse:272, window.drag) and clicks in apps are
-- untouched. A window is only carried while the cursor is still on it, so a missed release can't carry the wrong
-- one later.

local M = {}

-- Whether a point is inside a window's box (at and size are { x, y } tables, as hl's window objects give them).
function M.contains(window, point)
    if not window or not window.at or not window.size or not point then
        return false
    end
    local x, y = point.x, point.y
    return x >= window.at.x and x < window.at.x + window.size.x
       and y >= window.at.y and y < window.at.y + window.size.y
end

-- The window under the cursor on the visible workspaces: floating windows first, as they're drawn on top.
function M.window_at(windows, point, visible)
    local tiled
    for _, w in ipairs(windows or {}) do
        local ws = w.workspace
        if ws and (visible == nil or visible[ws.id]) and M.contains(w, point) then
            if w.floating then
                return w
            end
            tiled = tiled or w
        end
    end
    return tiled
end

-- Whether the noted window goes to a workspace that just became active: the cursor still on it (it follows the
-- cursor while dragged), not on that workspace already, and not a special workspace (the scratchpad).
function M.should_carry(window, workspace, cursor)
    if not window or not workspace or workspace.special then
        return false
    end
    if window.workspace and window.workspace.id == workspace.id then
        return false
    end
    return M.contains(window, cursor)
end

-- ── Wiring into Hyprland ───────────────────────────────────────────────────────────────────────────────────────

if rawget(_G, "hl") and hl.on and hl.get_windows then
    local carried = nil      -- the address of the window being dragged, or nil

    local function visibleWorkspaces()
        local visible = {}
        for _, m in ipairs(hl.get_monitors and hl.get_monitors() or {}) do
            local ws = m.active_workspace
            if ws then
                visible[ws.id] = true
            end
        end
        local ws = hl.get_active_workspace and hl.get_active_workspace()
        if ws then
            visible[ws.id] = true
        end
        return visible
    end

    local function byAddress(address)
        for _, w in ipairs(hl.get_windows() or {}) do
            if w.address == address then
                return w
            end
        end
        return nil
    end

    hl.bind("SUPER + mouse:272", function()
        local w = M.window_at(hl.get_windows(), hl.get_cursor_pos(), visibleWorkspaces())
        carried = w and w.address or nil
    end, { non_consuming = true })

    hl.bind("mouse:272", function()
        carried = nil
    end, { release = true, non_consuming = true, ignore_mods = true, submap_universal = true })

    hl.on("workspace.active", function(workspace)
        if not carried then
            return
        end
        local w = byAddress(carried)
        if not M.should_carry(w, workspace, hl.get_cursor_pos()) then
            if not w or not M.contains(w, hl.get_cursor_pos()) then
                carried = nil    -- the drag is over (or the window is gone)
            end
            return
        end
        hl.dispatch(hl.dsp.window.move({ workspace = tostring(workspace.id), follow = false, window = w }))
    end)
end

return M
