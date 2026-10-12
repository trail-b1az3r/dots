-- Hypr mode: a second layer of keybinds, so the same chords can do something else.
--
--   MODE.toggle   turns the mode on from anywhere, and turns it off again. It is a function key,
--                 Super and a letter held together. The default is SUPER + F10 + H.
--   MODE.exit     turns the mode off. Any key works here, and it is listed in MODE.
--
-- While the mode is on, the normal binds are off (that is how Hyprland submaps work), so each chord in
-- MODE_BINDS only has to be unique inside the mode. The same arrow keys can focus windows normally and move
-- them in the mode, for example. A chord that is not in the mode does nothing while it is on.
--
-- Add a mode bind with modeBind(chord, dispatcher, options), the same arguments as hl.bind, below.
-- The chords here are examples. Change them to suit.
--
-- Needs Hyprland with hl.define_submap and submap_universal (this fork and upstream 0.56 have both).

local MODE = {
    name   = "hypr",
    toggle = "SUPER + F10 + H",
    exit   = "Escape",
}

local MODE_BINDS = {}

local function modeBind(chord, dispatcher, options)
    table.insert(MODE_BINDS, { chord, dispatcher, options or {} })
end

-- Examples: in the mode, the arrow keys move the window (the normal arrows only change focus).
local arrowkey = { "Left", "Right", "Up", "Down" }
local focusdir = { "l", "r", "u", "d" }
for i = 1, 4 do
    modeBind(arrowkey[i], hl.dsp.window.move({ direction = focusdir[i] }),
        { description = "Hypr mode: Move window " .. arrowkey[i] })
end

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

    for _, b in ipairs(MODE_BINDS) do
        hl.bind(b[1], b[2], b[3])
    end
end)
