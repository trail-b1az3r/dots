-- hyprland-plus: the Halcyon fork's window types and drag options, set up for this desktop.
--
-- Needs the Halcyon Hyprland fork (it adds the superposition and plustile rules, hl.dsp.window.fit_plustile
-- and the superposition options). On stock Hyprland the dispatcher does not exist, so this file does nothing.
--
-- The drag options (binds:drag_keep_grab_point and binds:drag_guide) are on by default in the fork, so they
-- are not set here. Set them to false in ~/.config/hypr/custom if you want upstream's drag behaviour.
--
-- Superposition: a tiled window kept on a thin strip at the right edge, drawn above a fullscreen window.
-- Plustile: a tiled window that can be resized from each edge (SUPER + ALT + arrows, see tiles.lua).
if hl.dsp and hl.dsp.window and hl.dsp.window.fit_plustile then
    -- Strip at the right edge, 12% of the screen wide. It overlays the tiles (reserve = false).
    hl.config({ superposition = { edge = 1, size = 0.12, reserve = false } })

    -- Terminals can be resized per edge. Nothing changes until a SUPER + ALT key is pressed.
    hl.window_rule({ match = { class = "^(kitty|foot|Alacritty|org.wezfurlong.wezterm)$" }, plustile = true })

    -- A music player stays on the strip, so it is visible while another window is fullscreen.
    hl.window_rule({ match = { class = "^([Ss]potify)$" }, superposition = true })
end
