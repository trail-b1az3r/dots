-- The scratchpad, and finding lost windows.
--
-- Super + S shows and hides the scratchpad workspace and Super + Alt + S sends a window there (keybinds.lua). Next
-- to it, a drop-down terminal: Super + Z slides an Alacritty down from the top of the screen and back up, the same
-- one each time, so what you typed in it is still there. It lives on its own hidden workspace (special:dropdown).
--
-- Lost windows: windows that ended up off every screen (a monitor unplugged, a game that moved itself, a drag that
-- went too far). Super + Shift + W brings each of them back onto the current workspace, centred on the focused
-- monitor, and says how many it found. `halcyon lost` lists them in a terminal (halcyon_lost.py).

local M = {}

M.DROPDOWN_CLASS = "halcyon-dropdown"
M.DROPDOWN_WORKSPACE = "dropdown"

-- Whether a window's box touches any monitor. Windows on hidden special workspaces are not lost: they are put away.
function M.on_a_monitor(window, monitors)
    if not window or not window.at or not window.size then
        return true
    end
    for _, m in ipairs(monitors or {}) do
        -- Logical size: the mode divided by the scale.
        local scale = m.scale or 1
        local mx, my = m.x or 0, m.y or 0
        local mw, mh = (m.width or 0) / scale, (m.height or 0) / scale
        if window.at.x < mx + mw and window.at.x + window.size.x > mx
            and window.at.y < my + mh and window.at.y + window.size.y > my then
            return true
        end
    end
    return false
end

function M.lost(windows, monitors)
    local found = {}
    for _, w in ipairs(windows or {}) do
        local ws = w.workspace
        local hidden = ws and ws.special
        if not hidden and w.mapped ~= false and not M.on_a_monitor(w, monitors) then
            found[#found + 1] = w
        end
    end
    return found
end

if rawget(_G, "hl") and hl.bind then
    -- The drop-down terminal: floating, most of the screen's width, the top third, sliding from the top.
    hl.window_rule({ match = { class = "^(" .. M.DROPDOWN_CLASS .. ")$" }, float = true })
    hl.window_rule({ match = { class = "^(" .. M.DROPDOWN_CLASS .. ")$" }, size = { "(monitor_w*0.76)", "(monitor_h*0.42)" } })
    hl.window_rule({ match = { class = "^(" .. M.DROPDOWN_CLASS .. ")$" }, move = { "(monitor_w*0.12)", "(monitor_h*0.04)" } })
    hl.window_rule({ match = { class = "^(" .. M.DROPDOWN_CLASS .. ")$" }, workspace = "special:" .. M.DROPDOWN_WORKSPACE })
    hl.workspace_rule({ workspace = "special:" .. M.DROPDOWN_WORKSPACE, gaps_out = 0 })

    hl.bind("SUPER + Z", function()
        local running = false
        for _, w in ipairs(hl.get_windows and hl.get_windows() or {}) do
            if w.class == M.DROPDOWN_CLASS then
                running = true
                break
            end
        end
        if running then
            hl.dispatch(hl.dsp.workspace.toggle_special(M.DROPDOWN_WORKSPACE))
        else
            -- Its window rule puts it on the drop-down workspace; show that once it is there.
            hl.exec_cmd("alacritty --class " .. M.DROPDOWN_CLASS .. " & sleep 0.4; " ..
                "hyprctl dispatch 'hl.dsp.workspace.toggle_special(\"" .. M.DROPDOWN_WORKSPACE .. "\")' >/dev/null")
        end
    end, { description = "Workspace: Drop-down terminal" })

    hl.bind("SUPER + SHIFT + W", function()
        local lost = M.lost(hl.get_windows and hl.get_windows() or {}, hl.get_monitors and hl.get_monitors() or {})
        local ws = hl.get_active_workspace and hl.get_active_workspace()
        for _, w in ipairs(lost) do
            if ws then
                hl.dispatch(hl.dsp.window.move({ workspace = tostring(ws.id), follow = false, window = w }))
            end
            hl.dispatch(hl.dsp.focus({ window = "address:" .. w.address }))
            if not w.floating then
                hl.dispatch(hl.dsp.window.float({ action = "enable" }))
            end
            hl.dispatch(hl.dsp.window.center())
        end
        local text = #lost == 0 and "No lost windows: every window is on a screen or put away."
            or (#lost .. " lost window" .. (#lost == 1 and " is" or "s are") .. " back on this workspace.")
        hl.exec_cmd("notify-send -a Halcyon -i window-restore 'Lost windows' '" .. text .. "'")
    end, { description = "Window: Bring back lost windows" })
end

return M
