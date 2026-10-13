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
require("hyprland.halcyon.mini")
require("hyprland.halcyon.tiles")
require("hyprland.halcyon.plus")
require("hyprland.halcyon.modes")

-- The active theme's window style, written by halcyon-theme. It exists only
-- while a theme is active; see `halcyon-theme list`.
local stateHome = os.getenv("XDG_STATE_HOME") or (HOME .. "/.local/state")
local themeFile = stateHome .. "/halcyon/theme.lua"
if is_file_exists(themeFile) then
    dofile(themeFile)
end

-- Plus Tiles settings from Settings > Halcyon > Plus Tiles (halcyon-theme plus apply). They override the
-- defaults in plus.lua; custom/ is loaded later and still wins.
local plusFile = stateHome .. "/halcyon/plus.lua"
if is_file_exists(plusFile) then
    dofile(plusFile)
end

-- How new windows are split, from Settings > Interface > Windows (halcyon-theme placement).
local placementFile = stateHome .. "/halcyon/placement.lua"
if is_file_exists(placementFile) then
    dofile(placementFile)
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

-- The shell and the GPU guard run as systemd user services, so they restart
-- if they exit. The environment Hyprland set up is handed to systemd first, so
-- the services can find the display. Units live in ~/.config/systemd/user.
hl.on("hyprland.start", function()
    hl.exec_cmd("systemctl --user import-environment WAYLAND_DISPLAY HYPRLAND_INSTANCE_SIGNATURE " ..
        "XDG_RUNTIME_DIR DISPLAY XDG_CURRENT_DESKTOP; " ..
        "systemctl --user daemon-reload; " ..
        "systemctl --user restart halcyon-quickshell.service halcyon-gpu-guard.service halcyon-resume.service")
end)
