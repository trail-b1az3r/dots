-- Halcyon look: a little more air between windows, softer corners and a
-- deeper blur behind the shell's glass panels. Only keys that differ
-- from hyprland/general.lua are set here.
--
-- Border colours are deliberately not set: they come from the wallpaper
-- (hyprland/colors.lua, written by matugen) or from the active theme.

local function hasOption(key)
    if not (hl and hl.get_config) then
        return false
    end
    local ok, value = pcall(hl.get_config, key)
    return ok and value ~= nil
end

local hasBlurVariant = hasOption("decoration:blur:variant")
local hasBlurProportional = hasOption("decoration:blur:proportional")
local hasShaderBlurBlend = hasOption("render:use_shader_blur_blend")
local hasMotionBlur = hasOption("decoration:motion_blur:enabled")
local hasGlow = hasOption("decoration:glow:enabled")
local hasWobble = hasOption("decoration:wobble:enabled")

hl.config({
    general = {
        gaps_in = 5,
        gaps_out = 10,

        snap = {
            window_gap = 5,
            monitor_gap = 10
        }
    },
    decoration = {
        rounding = 20,

        blur = {
            size = 10,
            passes = 2,
            vibrancy = 0.6,
            -- Blur behind popups too, so menus read as the same glass as
            -- the panels they open from.
            popups = true
        },
        shadow = {
            range = 28,
            offset = {0, 4},
            color = "rgba(0000002E)"
        }
    }
})

-- Hyprland 0.57 renderer features. Each block is capability-gated so
-- existing 0.56/stock builds keep loading without unknown-option errors.
-- Acrylic is deliberately not selected: Kawase blur is lighter on integrated
-- GPUs while still benefiting from proportional blur.
if hasBlurVariant then
    -- Kawase is the low-overhead default variant (enum value 0).
    hl.config({ decoration = { blur = { variant = 0 } } })
end

if hasBlurProportional and hasShaderBlurBlend then
    hl.config({
        render = { use_shader_blur_blend = true },
        decoration = { blur = { proportional = true } }
    })
end

if hasMotionBlur then
    hl.config({ decoration = { motion_blur = { enabled = true, samples = 5 } } })
end

if hasGlow then
    hl.config({
        decoration = {
            glow = {
                enabled = true,
                range = 8,
                render_power = 3,
                color = "rgba(0DB7D455)"
            }
        }
    })
end

if hasWobble then
    hl.config({
        decoration = {
            wobble = {
                enabled = true,
                mesh = 8,
                stiffness = 220,
                damping = 18,
                intensity = 0.14
            }
        }
    })
end
