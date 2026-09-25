-- Halcyon keybinds. These only ADD chords that upstream leaves free;
-- nothing in hyprland/keybinds.lua is rebound or shadowed. The CI check
-- scripts/check-keybinds.py fails if that ever stops being true.
--
-- Descriptions use the same "Category: text" form as upstream so they
-- show up in the cheatsheet (Super + /) next to the built-in ones.

local qsScripts = "$HOME/.config/quickshell/$qsConfig/scripts"
local qsIpcCall = "qs -c $qsConfig ipc call"
local qsIsAlive = qsIpcCall .. " TEST_ALIVE"

--##! Halcyon
--# Launch
hl.bind("SUPER + Space", hl.dsp.global("quickshell:searchToggle"), { description = "Shell: Search" })
hl.bind("SUPER + Space", hl.dsp.exec_cmd(qsIsAlive .. " || pkill fuzzel || fuzzel"))
hl.bind("SUPER + Escape", hl.dsp.global("quickshell:sessionToggle"), { description = "Shell: Session menu" })
hl.bind("SUPER + Escape", hl.dsp.exec_cmd(qsIsAlive .. " || pkill wlogout || wlogout -p layer-shell"))
hl.bind("SUPER + Comma", hl.dsp.exec_cmd(settingsApp), { description = "App: Settings app" })

--# Workspaces
hl.bind("SUPER + grave", hl.dsp.focus({ workspace = "previous" }), { description = "Workspace: Back and forth" })

--# Capture, macOS-style
-- Sets $f to a fresh file in ~/Pictures/Screenshots, quoted for paths with spaces
local newScreenshotFile = "d=\"$(xdg-user-dir PICTURES)/Screenshots\" && mkdir -p \"$d\" && " ..
    "f=\"$d/Screenshot_$(date '+%Y-%m-%d_%H.%M.%S').png\""
local focusedMonitor = "\"$(hyprctl activeworkspace -j | jq -r '.monitor')\""
local activeWindowGeometry =
    "\"$(hyprctl activewindow -j | jq -r '\"\\(.at[0]),\\(.at[1]) \\(.size[0])x\\(.size[1])\"')\""

hl.bind("SUPER + SHIFT + 3", hl.dsp.exec_cmd(
    newScreenshotFile .. " && grim -o " .. focusedMonitor .. " \"$f\" && wl-copy < \"$f\""
), { locked = true, description = "Utilities: Screenshot screen >> clipboard & file" })

hl.bind("SUPER + SHIFT + 4", hl.dsp.global("quickshell:regionScreenshot"),
    { description = "Utilities: Screenshot region" })
hl.bind("SUPER + SHIFT + 4",
    hl.dsp.exec_cmd(qsIsAlive .. " || pidof slurp || hyprshot --freeze --clipboard-only --mode region --silent"))

hl.bind("SUPER + SHIFT + 5", hl.dsp.global("quickshell:regionRecord"),
    { locked = true, description = "Utilities: Record region" })
hl.bind("SUPER + SHIFT + 5", hl.dsp.exec_cmd(qsIsAlive .. " || " .. qsScripts .. "/videos/record.sh"),
    { locked = true })

hl.bind("SUPER + SHIFT + 6", hl.dsp.exec_cmd(
    newScreenshotFile .. " && grim -g " .. activeWindowGeometry .. " \"$f\" && wl-copy < \"$f\""
), { description = "Utilities: Screenshot window >> clipboard & file" })

--# Themes
hl.bind("CTRL + SUPER + SHIFT + T", hl.dsp.exec_cmd("$HOME/.config/hypr/hyprland/halcyon/halcyon-theme menu"),
    { description = "Shell: Pick a Halcyon theme" })

--# HyperNix, when installed
hl.bind("SUPER + SHIFT + H", hl.dsp.exec_cmd(
    "if command -v hypernix >/dev/null; then hypernix; else notify-send 'HyperNix is not installed' -a Hyprland; fi"
), { description = "App: HyperNix" })
