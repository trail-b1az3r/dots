-- Mini windows: a window made small, out of the way, and back to full size with a click. Super + Ctrl + N
-- does it to the focused window, tiled or floating; so do the down arrow on a floating window's title bar and
-- the bar's window buttons.
--
-- With the Halcyon Hyprland fork (hl.dsp.window.mini and the binds:mini_* options) Hyprland does it: the mini
-- window can be moved to any side of the screen and stays small, and a click on it, without moving it, brings it
-- back. On stock Hyprland the shell does it instead (services/MiniWindows.qml in quickshell): the window floats
-- and glides to a row of mini windows in the bottom right corner.
--
-- 240 × 150 is big enough to see what is in it and still out of the way; the shell's own minis are the same size.
local qsIpcCall = "qs -c $qsConfig ipc call"

if hl.dsp and hl.dsp.window and hl.dsp.window.mini then
    hl.config({ binds = { mini_width = 240, mini_height = 150 } })

    hl.bind("SUPER + CTRL + N", hl.dsp.window.mini(), { description = "Window: Make mini, or bring back to full size" })
else
    hl.bind("SUPER + CTRL + N", hl.dsp.exec_cmd(qsIpcCall .. " miniWindows toggleActive"),
        { description = "Window: Make mini, or bring back to full size" })
end
