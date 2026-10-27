-- A maximised tiled window covers the workspace and hides the other tiles, and there is then nothing to click to get
-- them back: it looked as if a terminal had eaten the other windows, until it was closed. Super + D (or M in hypr
-- mode) does it, easily by accident. So when a tiled window is maximised with other tiles behind it, a notification
-- says so, with a button that brings them back.

local M = {}

-- Hyprland's internal fullscreen state: 1 is maximised, 2 fullscreen (a bitmask).
M.MAXIMISED = 1

-- Whether to warn: the window is tiled, maximised (not fullscreen), and there are other tiled windows behind it.
function M.hides_others(window, windows)
    if not window or window.floating or window.fullscreen ~= M.MAXIMISED then
        return false
    end
    local ws = window.workspace
    for _, w in ipairs(windows or {}) do
        if w.address ~= window.address and not w.floating and w.workspace and ws and w.workspace.id == ws.id then
            return true
        end
    end
    return false
end

-- The shell command: the notification, and on its button, focus the window and un-maximise it.
function M.notify_command(window)
    local name = (window.class or "A window"):gsub("[^%w%._%- ]", "")
    local restore = string.format(
        "hyprctl dispatch 'hl.dsp.focus({ window = \"address:%s\" })' >/dev/null && " ..
        "hyprctl dispatch 'hl.dsp.window.fullscreen({ mode = \"maximized\", action = \"unset\" })' >/dev/null",
        window.address)
    return string.format(
        "a=$(notify-send -a Halcyon -i view-restore -t 12000 -A restore='Bring them back' " ..
        "'%s is maximised' 'The other windows are behind it. Super + D, or the button, brings them back.'); " ..
        "[ \"$a\" = restore ] && %s", name, restore)
end

if rawget(_G, "hl") and hl.on then
    hl.on("window.fullscreen", function(window)
        local ws = window and window.workspace
        if not ws then
            return
        end
        if M.hides_others(window, hl.get_workspace_windows(ws)) then
            hl.exec_cmd(M.notify_command(window))
        end
    end)
end

return M
