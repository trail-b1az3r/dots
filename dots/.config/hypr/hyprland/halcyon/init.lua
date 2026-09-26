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

-- The Halcyon Glass cursor (Settings > Halcyon > Cursor). Upstream sets its
-- own cursor at startup too, so wait a moment and apply ours after it.
hl.on("hyprland.start", function()
    hl.exec_cmd("sleep 1 && $HOME/.config/hypr/hyprland/halcyon/halcyon-theme cursor apply")
end)

-- The voice assistant daemon, if Settings > Halcyon > Assistant has it on.
hl.on("hyprland.start", function()
    hl.exec_cmd("log=\"${XDG_STATE_HOME:-$HOME/.local/state}/halcyon\"; mkdir -p \"$log\" && " ..
        "$HOME/.config/hypr/hyprland/halcyon/assistant/halcyon-assistant autostart >> \"$log/assistant.log\" 2>&1")
end)

-- A `halcyon` command for any shell: link it into ~/.local/bin at startup
-- (fish and zsh also get an alias). A real file already there is left alone.
hl.on("hyprland.start", function()
    hl.exec_cmd("bin=\"$HOME/.local/bin/halcyon\"; " ..
        "if [ ! -e \"$bin\" ] || [ -L \"$bin\" ]; then " ..
        "mkdir -p \"$HOME/.local/bin\" && ln -sfn \"$HOME/.config/hypr/hyprland/halcyon/halcyon-theme\" \"$bin\"; fi")
end)
