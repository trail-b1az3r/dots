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
        { "Left",  hl.dsp.window.move({ direction = "l" }), "Hypr mode: Move window left" },
        { "Right", hl.dsp.window.move({ direction = "r" }), "Hypr mode: Move window right" },
        { "Up",    hl.dsp.window.move({ direction = "u" }), "Hypr mode: Move window up" },
        { "Down",  hl.dsp.window.move({ direction = "d" }), "Hypr mode: Move window down" },
    },
}
