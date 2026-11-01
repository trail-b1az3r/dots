-- The super battery saver (halcyon saver, halcyon_saver.py): while it is on, the screen is
-- drawn at most 12 times a second (hyprland-plus's plus:max_fps; plain Hyprland skips that part), unfocused windows
-- are capped at 10 FPS, and animations and GPU-heavy decorations are off. The saver reloads the config when it turns
-- on or off; this file reads whether it is.

local C = require("hyprland.halcyon.compositor")

local stateHome = os.getenv("XDG_STATE_HOME") or ((os.getenv("HOME") or "") .. "/.local/state")
local file = io.open(stateHome .. "/halcyon/saver.json", "r")
if not file then
    return
end
local text = file:read("*a") or ""
file:close()

hl.config({
    animations = { enabled = false },
    decoration = { blur = { enabled = false }, shadow = { enabled = false } },
})

-- These options do not exist on every supported compositor build.
if C.motionBlur then
    hl.config({ decoration = { motion_blur = { enabled = false } } })
end
if C.glow then
    hl.config({ decoration = { glow = { enabled = false } } })
end
if C.wobble then
    hl.config({ decoration = { wobble = { enabled = false } } })
end

hl.config({ misc = { render_unfocused_fps = 10 } })

if C.maxFps then
    hl.config({ plus = { max_fps = tonumber(text:match('"max_fps"%s*:%s*(%d+)')) or 12 } })
end
