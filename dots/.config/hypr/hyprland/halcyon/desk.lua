-- hyprland-plus 0.56.2.p2 additions (the wiki's Desk page). On older builds and stock Hyprland this file does nothing.
--   SUPER + ALT + D            Desktop peek: the windows fade and the wallpaper's widgets (the revolver) take the pointer.
--                              Again to bring the windows back.
--   SUPER + CTRL + SHIFT + N   Every window on the workspace mini, in a row along the bottom; again to bring them back
--   SUPER + CTRL + period      Show where the pointer is. Shaking the mouse does it too.
if not (hl.dsp and hl.dsp.plus and hl.dsp.plus.peek) then
    return
end

hl.config({ plus = { shake_to_find = true } })

hl.bind("SUPER + ALT + D", hl.dsp.plus.peek(), { description = "Desktop: Peek at the desktop, or back" })
hl.bind("SUPER + CTRL + SHIFT + N", hl.dsp.plus.mini_all(), { description = "Windows: All mini, or all back" })
hl.bind("SUPER + CTRL + period", hl.dsp.plus.locate_pointer(), { description = "Pointer: Show where it is" })
