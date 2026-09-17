-- Halcyon — Hyprland configuration.
--
-- This file is yours to edit. It loads Halcyon's modules and then, at the
-- very end, your own overrides from `local.lua` — so nothing you write
-- there can be undone by an update.
--
-- Everything that the Settings app can change lives in generated files
-- under ~/.config/halcyon/generated/ and is loaded by halcyon/generated.lua.
-- Do not edit those; edit settings.json (or use Settings) and run
-- `halcyon theme apply`.
--
-- Requires Hyprland 0.56 or newer, which configures in Lua.

------------------------------------------------------------------------
-- Halcyon modules
------------------------------------------------------------------------

-- Each require() is its own error scope in Hyprland: a mistake in one
-- file does not stop the others from loading, which is what keeps a
-- broken edit from leaving you with no keybinds at all.
require("halcyon.generated")   -- theme, animations, keybinds, rules (generated)
require("halcyon.appearance")  -- look and feel that is not theme-derived
require("halcyon.behaviour")   -- window behaviour, layouts, gestures
require("halcyon.autostart")   -- the services that make up the desktop

------------------------------------------------------------------------
-- Your overrides
------------------------------------------------------------------------

-- `local.lua` is created empty on install and never touched again, so
-- this is the safe place for anything personal. pcall keeps a syntax
-- error there from taking the rest of the session down with it.
do
    local ok, err = pcall(require, "local")
    if not ok and not tostring(err):match("module 'local' not found") then
        hl.notification.create({
            text = "Halcyon: local.lua failed to load — " .. tostring(err),
            timeout = 12000,
            icon = 3,
        })
    end
end
