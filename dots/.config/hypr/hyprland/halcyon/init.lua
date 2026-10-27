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
-- SUPER + drag a window, then switch workspace: the window comes along (carry.lua).
require("hyprland.halcyon.carry")

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

-- Halcyon's own layouts (two at a time, stacked or side by side, and the Mondrian grid), registered so
-- placement.lua can pick one; see layouts.lua.
require("hyprland.halcyon.layouts")

-- Whether games keep the keyboard when the pointer leaves them (games.lua; Settings > Halcyon > Games).
local gamesFile = stateHome .. "/halcyon/games.lua"
if is_file_exists(gamesFile) then
    dofile(gamesFile)
end
require("hyprland.halcyon.games")

-- Which volume and brightness popup is on, and whether the drawing overlay starts at login (overlays.lua).
local overlaysFile = stateHome .. "/halcyon/overlays.lua"
if is_file_exists(overlaysFile) then
    dofile(overlaysFile)
end
require("hyprland.halcyon.overlays")
require("hyprland.halcyon.desk")

-- How new windows are placed, from Settings > Interface > Windows (halcyon-theme placement).
local placementFile = stateHome .. "/halcyon/placement.lua"
if is_file_exists(placementFile) then
    dofile(placementFile)
end

-- The Halcyon Glass cursor (Settings > Halcyon > Cursor). Upstream sets its
-- own cursor at startup too, so wait a moment and apply ours after it.
hl.on("hyprland.start", function()
    hl.exec_cmd("sleep 1 && $HOME/.config/hypr/hyprland/halcyon/halcyon-theme cursor apply")
end)

-- A theme applied by an older Halcyon is brought up to date, and Firefox and Chromium get the current colours
-- (a profile made since the last theme change is themed too). After the shell is up, since the theme may change
-- its settings.
hl.on("hyprland.start", function()
    hl.exec_cmd("sleep 4 && $HOME/.config/hypr/hyprland/halcyon/halcyon-theme migrate >/dev/null 2>&1")
end)

-- Wi-Fi at login: wait for the card (a Surface's is slow), unblock the radio, take back a device NetworkManager left
-- unmanaged, and connect. `halcyon wifi` says what is in the way; its log is ~/.local/state/halcyon/wifi.log.
hl.on("hyprland.start", function()
    hl.exec_cmd("python3 $HOME/.config/hypr/hyprland/halcyon/halcyon_wifi.py boot >/dev/null 2>&1")
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
        -- Older Halcyon enabled these for every login, which started the shell in KDE too. They are only
        -- started from here now, so drop those links.
        "w=\"${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/default.target.wants\"; " ..
        "rm -f \"$w/halcyon-quickshell.service\" \"$w/halcyon-gpu-guard.service\" \"$w/halcyon-resume.service\"; " ..
        "systemctl --user restart halcyon-quickshell.service halcyon-gpu-guard.service halcyon-resume.service; " ..
        -- The hourly update check. An install made before it existed, or a timer turned off by mistake, gets it.
        "systemctl --user enable --now halcyon-update.timer >/dev/null 2>&1; " ..
        -- Server mode (Settings > Halcyon) stays on across restarts.
        "$HOME/.config/hypr/hyprland/halcyon/halcyon_server.py apply")
end)
