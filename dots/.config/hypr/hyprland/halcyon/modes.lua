-- Hypr mode: a second layer of keybinds, so the same chords can do something else.
--
-- The keys and binds are in hypr_mode.lua (or your copy in ~/.config/hypr/custom/hypr_mode.lua). This file
-- only turns the mode on and off and registers the binds. Edit hypr_mode.lua to change them.
--
-- Needs Hyprland with hl.define_submap and submap_universal (this fork and upstream 0.56 have both).

local function loadSettings()
    local userFile = HOME .. "/.config/hypr/custom/hypr_mode.lua"
    if is_file_exists(userFile) then
        return dofile(userFile)
    end
    return require("hyprland.halcyon.hypr_mode")
end

local SETTINGS = loadSettings()
local MODE     = { name = "hypr", exit = SETTINGS.exit }

-- toggle is one chord or a list of them.
MODE.toggles   = type(SETTINGS.toggle) == "table" and SETTINGS.toggle or { SETTINGS.toggle }

-- The shell shows the mode (a swipe, then the mode's binds) when the submap changes. Without the shell running,
-- a notification says it instead.
local QS_ALIVE = "qs -c $qsConfig ipc call TEST_ALIVE >/dev/null 2>&1"

-- The mode turns itself off when none of its keys has been used for a while (hypr_mode.lua: idle_exit).
local IDLE_EXIT = tonumber(SETTINGS.idle_exit or 10) or 10
local idleTimer = nil
local exitMode

local function stopIdle()
    if idleTimer and idleTimer.set_enabled then
        idleTimer:set_enabled(false)
    end
    idleTimer = nil
end

local function armIdle()
    stopIdle()
    if IDLE_EXIT <= 0 or not hl.timer then
        return
    end
    idleTimer = hl.timer(function()
        if hl.get_current_submap() == MODE.name then
            exitMode()
        end
    end, { timeout = IDLE_EXIT * 1000, type = "oneshot" })
end

local function enterMode()
    armIdle()
    hl.dispatch(hl.dsp.submap(MODE.name))
    hl.dispatch(hl.dsp.exec_cmd(QS_ALIVE .. " || notify-send 'Entered hypr mode' 'Keybinds are different until you press " .. MODE.exit .. "' -a 'Hyprland'"))
end

exitMode = function()
    stopIdle()
    hl.dispatch(hl.dsp.submap("reset"))
    hl.dispatch(hl.dsp.exec_cmd(QS_ALIVE .. " || notify-send 'Left hypr mode' 'Keybinds are back to normal' -a 'Hyprland'"))
end

-- The toggle is universal, so it works both outside the mode and inside it.
local function toggleMode()
    local current = hl.get_current_submap()
    if current == MODE.name then
        exitMode()
    elseif current == "" then
        enterMode()
    end
end

hl.define_submap(MODE.name, function()
    for i, chord in ipairs(MODE.toggles) do
        -- Only the first one is described, so the cheat sheet lists the mode once.
        hl.bind(chord, toggleMode, { submap_universal = true, description = i == 1 and "Shell: Toggle hypr mode" or nil })
    end
    hl.bind(MODE.exit, exitMode)

    for _, b in ipairs(SETTINGS.binds) do
        local action = b[2]
        -- Each key used keeps the mode on a while longer.
        hl.bind(b[1], function()
            armIdle()
            if type(action) == "function" then
                action()
            else
                hl.dispatch(action)
            end
        end, { description = b[3] })
    end
end)
