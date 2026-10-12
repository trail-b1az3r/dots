-- Mini windows: a window made very small (hl.dsp.window.mini) that can be moved to any side of the
-- screen and fitted around the others. A click on it, without moving it, brings it back to full size.
--
-- These need the Halcyon Hyprland fork, which adds hl.dsp.window.mini and the binds:mini_* options.
-- On stock Hyprland the dispatcher does not exist, so this file does nothing and the title bar's own
-- mini windows are used instead (see floatingTitleBars in quickshell).
if hl.dsp and hl.dsp.window and hl.dsp.window.mini then
    hl.config({ binds = { mini_width = 96, mini_height = 54 } })

    hl.bind("SUPER + CTRL + N", hl.dsp.window.mini(), { description = "Window: Make mini, or bring back to full size" })
end
