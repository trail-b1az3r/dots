-- Halcyon — loads everything the Settings app generates.
--
-- The files required here are written by `halcyon theme apply` from
-- settings.json. They are not in this repository and must not be edited
-- by hand: the next settings change overwrites them.
--
-- If they are missing — a fresh clone, or a cleared config — this module
-- falls back to a plain, working desktop and says so, rather than
-- leaving you at a black screen with no keybinds.

local config_home = os.getenv("XDG_CONFIG_HOME") or (os.getenv("HOME") .. "/.config")
local generated = config_home .. "/halcyon/generated"

local function load_generated(name)
    local path = generated .. "/" .. name .. ".lua"
    local chunk, err = loadfile(path)
    if not chunk then
        return false, err
    end
    local ok, run_err = pcall(chunk)
    if not ok then
        return false, run_err
    end
    return true
end

-- hypr-theme returns a table rather than applying anything, so it is
-- loaded separately and handed to appearance.lua through a global.
local function load_theme()
    local chunk = loadfile(generated .. "/hypr-theme.lua")
    if not chunk then
        return nil
    end
    local ok, value = pcall(chunk)
    if ok and type(value) == "table" then
        return value
    end
    return nil
end

HALCYON_THEME = load_theme()

local missing = {}
for _, name in ipairs({ "hypr-runtime", "hypr-animations", "hypr-keybinds" }) do
    local ok = load_generated(name)
    if not ok then
        table.insert(missing, name)
    end
end

if #missing > 0 or HALCYON_THEME == nil then
    -- Enough of a desktop to fix the problem from: a terminal, a way to
    -- close a window, and a way to get out.
    hl.bind("SUPER + Return", hl.dsp.exec_cmd("kitty || foot || alacritty || xterm"))
    hl.bind("SUPER + W", hl.dsp.window.close())
    hl.bind("SUPER + CTRL + ESCAPE", hl.dsp.exit())
    hl.config({ general = { border_size = 2, gaps_in = 5, gaps_out = 12 } })

    hl.notification.create({
        text = "Halcyon: generated config missing — run `halcyon theme apply`",
        timeout = 20000,
        icon = 0,
    })
end
