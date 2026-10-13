-- Super on its own opens the overview (the hyper key menu) when it is released. A key pressed while Super is held
-- must cancel that, or Super + / would open the cheat sheet and then the overview as well.
--
-- The cancel is quickshell's searchToggleReleaseInterrupt. It used to come from a catch-all bind, but a catch-all
-- that ignores modifiers also catches the Super key itself: every tap cancelled its own toggle, so the menu never
-- opened. Instead, every bind whose chord holds Super gets a companion bind on the same chord that sends the
-- interrupt. Companions only fire for real Super combinations, never for Super alone. They are non-consuming and
-- transparent, so the chord's own bind still runs and is not shadowed, and they have no description, so the cheat
-- sheet does not list them.
--
-- This file wraps hl.bind, so it must be loaded before the first bind (keybinds.lua requires it first).

if HALCYON_SUPER_TAP_WRAPPED then
    return
end
HALCYON_SUPER_TAP_WRAPPED = true

local INTERRUPT  = "quickshell:searchToggleReleaseInterrupt"
local SUPER_MODS = { SUPER = true, MOD4 = true, WIN = true, LOGO = true }
local NOT_A_KEY  = { SUPER_L = true, SUPER_R = true, CATCHALL = true }

-- True for "SUPER + X", "SUPER + SHIFT + X", "SUPER + F10 + H", "SUPER + mouse:272"; false for "SUPER + SUPER_L",
-- for chords without Super, and for anything that is not a string.
local function holdsSuper(chord)
    if type(chord) ~= "string" then
        return false
    end
    local parts = {}
    for part in chord:gmatch("[^+]+") do
        parts[#parts + 1] = part:match("^%s*(.-)%s*$")
    end
    if #parts < 2 or NOT_A_KEY[parts[#parts]:upper()] then
        return false
    end
    for i = 1, #parts - 1 do
        if SUPER_MODS[parts[i]:upper()] then
            return true
        end
    end
    return false
end

local originalBind = hl.bind

hl.bind = function(chord, action, opts)
    local result = originalBind(chord, action, opts)
    -- A release bind fires after Super is up, too late to cancel anything.
    if holdsSuper(chord) and not (type(opts) == "table" and opts.release) then
        originalBind(chord, hl.dsp.global(INTERRUPT), {
            non_consuming = true,
            transparent = true,
            submap_universal = type(opts) == "table" and opts.submap_universal or nil,
        })
    end
    return result
end

return { holdsSuper = holdsSuper }
