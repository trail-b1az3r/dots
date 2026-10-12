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
local MODE     = { name = "hypr", toggle = SETTINGS.toggle, exit = SETTINGS.exit }

local function enterMode()
    hl.dispatch(hl.dsp.exec_cmd("notify-send 'Entered hypr mode' 'Keybinds are different until you press " .. MODE.exit .. "' -a 'Hyprland'"))
    hl.dispatch(hl.dsp.submap(MODE.name))
end

local function exitMode()
    hl.dispatch(hl.dsp.exec_cmd("notify-send 'Left hypr mode' 'Keybinds are back to normal' -a 'Hyprland'"))
    hl.dispatch(hl.dsp.submap("reset"))
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
    hl.bind(MODE.toggle, toggleMode, { submap_universal = true, description = "Shell: Toggle hypr mode" })
    hl.bind(MODE.exit, exitMode)

    for _, b in ipairs(SETTINGS.binds) do
        hl.bind(b[1], b[2], { description = b[3] })
    end
end)
