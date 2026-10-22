-- Hypr mode keybinds. Edit this file to change them. Hyprland reloads when you save.
--
-- To keep your own version through Halcyon updates, copy this file to
-- ~/.config/hypr/custom/hypr_mode.lua and edit that copy. It is used instead of this one.
--
--   toggle   Turns the mode on from anywhere, and off again. One chord, or a list of chords.
--            Hold Super, then press the keys in the order written: for "SUPER + F10 + H", F10 before H.
--            On many laptops F10 is a media key unless Fn is held too, so SUPER + CTRL + H is there as well.
--   exit     Turns the mode off. Any key.
--   binds    The chords that work in the mode, as { chord, dispatcher, description }.
--            While the mode is on the normal binds are off, so a chord here can do something else
--            from the same chord outside the mode. A chord that is not listed does nothing in the mode.
--
-- The chord syntax is the same as hl.bind. Dispatchers are the same as hl.dsp.*, or a function.

return {
    toggle = { "SUPER + F10 + H", "SUPER + CTRL + H" },
    exit = "Escape",

    binds = {
        -- Move with the arrows, grow and shrink with Shift, focus with H J K L (vim's directions).
        { "Left",  hl.dsp.window.move({ direction = "l" }), "Hypr mode: Move window left" },
        { "Right", hl.dsp.window.move({ direction = "r" }), "Hypr mode: Move window right" },
        { "Up",    hl.dsp.window.move({ direction = "u" }), "Hypr mode: Move window up" },
        { "Down",  hl.dsp.window.move({ direction = "d" }), "Hypr mode: Move window down" },
        { "SHIFT + Right", hl.dsp.window.resize({ x = 40, y = 0, relative = true }),  "Hypr mode: Wider" },
        { "SHIFT + Left",  hl.dsp.window.resize({ x = -40, y = 0, relative = true }), "Hypr mode: Narrower" },
        { "SHIFT + Down",  hl.dsp.window.resize({ x = 0, y = 40, relative = true }),  "Hypr mode: Taller" },
        { "SHIFT + Up",    hl.dsp.window.resize({ x = 0, y = -40, relative = true }), "Hypr mode: Shorter" },
        { "H", hl.dsp.focus({ direction = "l" }), "Hypr mode: Focus left" },
        { "J", hl.dsp.focus({ direction = "d" }), "Hypr mode: Focus down" },
        { "K", hl.dsp.focus({ direction = "u" }), "Hypr mode: Focus up" },
        { "L", hl.dsp.focus({ direction = "r" }), "Hypr mode: Focus right" },
        -- The window itself.
        { "F", hl.dsp.window.float({ action = "toggle" }), "Hypr mode: Float or tile" },
        { "C", hl.dsp.window.center(), "Hypr mode: Center a floating window" },
        { "P", hl.dsp.window.pin(), "Hypr mode: Pin on every workspace" },
        { "M", hl.dsp.window.fullscreen({ mode = "maximized", action = "toggle" }), "Hypr mode: Maximise" },
        { "Tab", function()
            hl.dispatch(hl.dsp.window.cycle_next({ floating = true }))
            hl.dispatch(hl.dsp.window.bring_to_top())
        end, "Hypr mode: Next floating window on top" },
        -- Send the window to workspace 1 to 5 and stay here.
        { "1", hl.dsp.window.move({ workspace = "1", follow = false }), "Hypr mode: Send to workspace 1" },
        { "2", hl.dsp.window.move({ workspace = "2", follow = false }), "Hypr mode: Send to workspace 2" },
        { "3", hl.dsp.window.move({ workspace = "3", follow = false }), "Hypr mode: Send to workspace 3" },
        { "4", hl.dsp.window.move({ workspace = "4", follow = false }), "Hypr mode: Send to workspace 4" },
        { "5", hl.dsp.window.move({ workspace = "5", follow = false }), "Hypr mode: Send to workspace 5" },
    },
}
