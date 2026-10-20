-- Avizo (the volume and brightness popup) and Wayscriber (drawing on the screen, called Hyprmarker before it was
-- renamed). Settings > Halcyon > On the screen, or `halcyon osd` and `halcyon annotate`, change them; the choices
-- come from ~/.local/state/halcyon/overlays.lua (loaded by init.lua before this file).
--
--   SUPER + SHIFT + D   show or hide the drawing overlay (pen, shapes, text, whiteboard)
--
-- Both tools are optional: with one missing, its part of this file does nothing.
local halcyon = "$HOME/.config/hypr/hyprland/halcyon/halcyon-theme"

if HALCYON_OSD == "avizo" then
    hl.on("hyprland.start", function()
        hl.exec_cmd("command -v avizo-service >/dev/null 2>&1 && { pgrep -x avizo-service >/dev/null || avizo-service; }")
    end)
end

if HALCYON_ANNOTATE ~= false then
    hl.on("hyprland.start", function()
        -- After the shell is up, so the overlay's tray icon finds a tray.
        hl.exec_cmd("sleep 3; command -v wayscriber >/dev/null 2>&1 && { pgrep -x wayscriber >/dev/null || wayscriber --daemon; }")
    end)
end

hl.bind("SUPER + SHIFT + D", hl.dsp.exec_cmd(halcyon .. " annotate toggle"), { description = "Screen: Draw on the screen" })
