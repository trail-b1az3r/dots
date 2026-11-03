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

-- Blur: Kawase with 2 passes of 10 is the lightest blur that still reads as glass. Layers use xray (rules.lua), so
-- they blur only the wallpaper, which Hyprland caches, not the windows behind them.
local hasBlurVariant = hasOption("decoration:blur:variant")
local hasBlurProportional = hasOption("decoration:blur:proportional")
local hasShaderBlurBlend = hasOption("render:use_shader_blur_blend")
local hasMotionBlur = hasOption("decoration:motion_blur:enabled")
local hasGlow = hasOption("decoration:glow:enabled")
local hasWobble = hasOption("decoration:wobble:enabled")
local hasPressureCurve = hasOption("input:tablettool:pressure_curve")
local hasPressureSpeed = hasOption("input:tablettool:pressure_speed")
local hasPressureTilt = hasOption("input:tablettool:pressure_tilt")

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
    -- Three samples look the same as five while a window moves, for three fifths of the work.
    hl.config({ decoration = { motion_blur = { enabled = true, samples = 3 } } })
end

-- Fullscreen games and video go straight to the screen, skipping composition, whenever the app says it is a
-- game or video (2 = automatic). Saves a full-screen copy every frame.
if hasOption("render:direct_scanout") then
    hl.config({ render = { direct_scanout = 2 } })
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

-- The compositor applies the non-linear curve only inside supported painting apps.
-- Text input, handwriting and ordinary desktop interactions keep raw pen pressure.
if hasPressureCurve or hasPressureSpeed or hasPressureTilt then
    local tablettool = {}
    if hasPressureCurve then tablettool.pressure_curve = "soft" end
    if hasPressureSpeed then tablettool.pressure_speed = 0.15 end
    if hasPressureTilt then tablettool.pressure_tilt = 0.10 end
    hl.config({ input = { tablettool = tablettool } })
end
