-- Halcyon: this repository's layer on top of end-4's illogical-impulse.
--
-- Everything Halcyon changes about Hyprland lives in this folder, loaded
-- after the upstream defaults and before ~/.config/hypr/custom, so:
--   * upstream files stay untouched and upstream fixes merge cleanly;
--   * your own custom/*.lua still wins over anything set here.
--
-- To drop a part of the layer, comment out its line below.

require("hyprland.halcyon.general")
require("hyprland.halcyon.keybinds")

-- The active theme's window style, written by halcyon-theme. It exists only
-- while a theme is active; see `halcyon-theme list`.
local stateHome = os.getenv("XDG_STATE_HOME") or (HOME .. "/.local/state")
local themeFile = stateHome .. "/halcyon/theme.lua"
if is_file_exists(themeFile) then
    dofile(themeFile)
end
