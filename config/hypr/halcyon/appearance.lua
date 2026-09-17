-- Halcyon — look and feel.
--
-- Reads the palette and glass numbers that `halcyon theme apply` derived
-- from the wallpaper, and applies the parts of them that belong to the
-- compositor: window borders, corner radius, blur behind translucent
-- surfaces, and shadows.
--
-- The numbers themselves are not decided here. Change them in Settings →
-- Liquid Glass, or in settings.json.

local theme = HALCYON_THEME
if type(theme) ~= "table" then
    return
end

hl.config({
    general = {
        border_size = theme.borderSize or 1,
        gaps_in = theme.gapsIn or 6,
        gaps_out = theme.gapsOut or 14,
        gaps_workspaces = theme.gapsWorkspaces or 0,
        resize_on_border = true,
        extend_border_grab_area = 12,
        hover_icon_on_border = true,

        col = {
            -- A two-stop gradient across the focused window's border is
            -- what reads as "lit from one side" rather than "outlined".
            active_border = {
                colors = { theme.borderActive, theme.borderActiveEnd },
                angle = 45,
            },
            inactive_border = theme.borderInactive,
        },

        snap = {
            enabled = true,
            border_overlap = true,
            monitor_gap = 12,
            window_gap = 10,
        },
    },

    decoration = {
        rounding = theme.rounding or 16,
        -- Above 2.0 the corner becomes a squircle: the curvature eases in
        -- rather than starting abruptly, which is most of why Apple's
        -- corners look softer than a plain radius at the same size.
        rounding_power = theme.roundingPower or 2.0,

        active_opacity = theme.activeOpacity or 1.0,
        inactive_opacity = theme.inactiveOpacity or 1.0,
        fullscreen_opacity = 1.0,

        dim_inactive = false,
        dim_strength = 0.12,
        dim_special = 0.35,
        dim_around = 0.55,

        blur = {
            enabled = theme.blur.enabled,
            size = theme.blur.size,
            passes = theme.blur.passes,
            -- Without this the blur is recomputed for every layer on
            -- every frame; with it, only damaged regions are.
            new_optimizations = theme.blur.newOptimizations,
            -- Floating windows ignore tiled ones in their blur. A large
            -- saving on fill rate, at the cost of a little realism.
            xray = theme.blur.xray,
            vibrancy = theme.blur.vibrancy,
            vibrancy_darkness = theme.blur.vibrancyDarkness,
            noise = theme.blur.noise,
            brightness = theme.blur.brightness,
            contrast = theme.blur.contrast,
            -- Blurring behind the special workspace costs a full extra
            -- pass for a surface that is usually covered anyway.
            special = theme.blur.special,
            popups = theme.blur.popups,
            popups_ignorealpha = theme.blur.popupsIgnoreAlpha,
            ignore_opacity = theme.blur.ignoreOpacity,
        },

        shadow = {
            enabled = theme.shadow.enabled,
            range = theme.shadow.range,
            render_power = theme.shadow.renderPower,
            scale = theme.shadow.scale,
            sharp = theme.shadow.sharp,
            color = theme.shadowColor,
        },
    },

    misc = {
        background_color = theme.background,
        font_family = theme.font,
    },
})

if theme.cursorTheme and theme.cursorTheme ~= "" then
    hl.config({ cursor = { enable_hyprcursor = true } })
end
