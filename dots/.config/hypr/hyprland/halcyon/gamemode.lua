-- Game mode (Summit's side menu): while ~/.local/state/halcyon/gamemode.json exists, no animations, blur, shadows,
-- gaps or rounding, thin borders, and tearing allowed, so a game gets every frame and the least latency. The side menu
-- writes or removes the file and reloads Hyprland; this file reads whether it is there.

local stateHome = os.getenv("XDG_STATE_HOME") or ((os.getenv("HOME") or "") .. "/.local/state")
local file = io.open(stateHome .. "/halcyon/gamemode.json", "r")
if not file then
    return
end
file:close()

hl.config({
    animations = { enabled = false },
    decoration = { rounding = 0, blur = { enabled = false }, shadow = { enabled = false } },
    general = { gaps_in = 0, gaps_out = 0, border_size = 1, allow_tearing = true },
})
