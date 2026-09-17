-- Halcyon — how windows and workspaces behave.
--
-- The parts of window management that are a design decision rather than
-- a setting. Anything a user is likely to want different lives in
-- settings.json and arrives through halcyon/generated.lua instead.

hl.config({
    general = {
        layout = "dwindle",
        no_focus_fallback = false,
        resize_corner = 0,
    },

    binds = {
        -- Pressing the current workspace's key again returns you to the
        -- previous one, which is how macOS's Spaces shortcuts behave.
        workspace_back_and_forth = true,
        allow_workspace_cycles = true,
        -- Moving focus past the edge of a fullscreen window should leave
        -- it, not cycle inside it.
        movefocus_cycles_fullscreen = false,
        focus_preferred_method = 0,
        drag_threshold = 4,
    },

    misc = {
        -- Swallowing hides a terminal while the GUI it launched is open.
        -- Off by default: it surprises people who did not ask for it.
        enable_swallow = false,
        focus_on_activate = true,
        -- An application that stops responding gets a dialog rather than
        -- a frozen desktop.
        enable_anr_dialog = true,
        anr_missed_pings = 8,
        initial_workspace_tracking = 1,
        close_special_on_empty = true,
        mouse_move_focuses_monitor = true,
        exit_window_retains_fullscreen = false,
        session_lock_blur = true,
        session_lock_xray = false,
    },

    input = {
        special_fallthrough = true,
        focus_on_close = 1,
        mouse_refocus = true,
    },

    layout = {
        -- Stop a lone window on a wide monitor from stretching to the
        -- full width, where line lengths become unreadable.
        single_window_aspect_ratio = { 21, 9 },
        single_window_aspect_ratio_tolerance = 0.12,
    },

    group = {
        auto_group = false,
        drag_into_group = 1,
        merge_groups_on_drag = true,
        insert_after_current = true,

        groupbar = {
            enabled = true,
            stacked = false,
            height = 18,
            indicator_height = 3,
            indicator_gap = 3,
            gradients = false,
            render_titles = true,
            font_size = 11,
            rounding = 8,
            gaps_in = 3,
            gaps_out = 4,
            keep_upper_gap = true,
            scrolling = false,
        },
    },

    cursor = {
        -- Hiding the pointer while typing is right for a text editor and
        -- wrong for a drawing app; leaving it visible is the safer default.
        hide_on_key_press = false,
        hide_on_touch = true,
        inactive_timeout = 6,
        no_warps = false,
        persistent_warps = true,
        warp_on_change_workspace = 2,
        warp_on_toggle_special = 1,
    },

    render = {
        -- Direct scanout hands a fullscreen window straight to the
        -- display controller, skipping composition entirely. Large win
        -- for games and video; no effect elsewhere.
        direct_scanout = 1,
        expand_undersized_textures = true,
    },
})

------------------------------------------------------------------------
-- Layouts
------------------------------------------------------------------------

hl.config({
    dwindle = {
        preserve_split = true,
        smart_split = false,
        smart_resizing = true,
        force_split = 2,           -- new windows open to the right/below
        split_width_multiplier = 1.0,
        default_split_ratio = 1.0,
        special_scale_factor = 0.94,
        use_active_for_splits = true,
    },

    master = {
        new_status = "master",
        new_on_top = false,
        mfact = 0.55,
        orientation = "left",
        smart_resizing = true,
        allow_small_split = false,
        center_master_fallback = "left",
        special_scale_factor = 0.94,
    },

    scrolling = {
        column_width = 0.5,
        follow_focus = true,
        wrap_focus = false,
        fullscreen_on_one_column = true,
        focus_fit_method = 0,
    },
})

------------------------------------------------------------------------
-- Window swallowing exceptions
------------------------------------------------------------------------

-- Kept next to the option that uses them so turning swallowing on in
-- Settings does not also require hunting for the exception list.
hl.config({
    misc = {
        swallow_regex = "^(kitty|foot|Alacritty|org\\.wezfurlong\\.wezterm|com\\.mitchellh\\.ghostty)$",
        swallow_exception_regex = "^(wev|imv|mpv|nsxiv)$",
    },
})

------------------------------------------------------------------------
-- Submaps
------------------------------------------------------------------------

-- A resize mode, because dragging borders on a tiling layout is fiddly
-- and holding a modifier for every nudge is worse.
hl.define_submap("resize", function()
    hl.bind("left", hl.dsp.window.resize({ x = -60, y = 0, relative = true }), { repeating = true })
    hl.bind("right", hl.dsp.window.resize({ x = 60, y = 0, relative = true }), { repeating = true })
    hl.bind("up", hl.dsp.window.resize({ x = 0, y = -60, relative = true }), { repeating = true })
    hl.bind("down", hl.dsp.window.resize({ x = 0, y = 60, relative = true }), { repeating = true })
    hl.bind("h", hl.dsp.window.resize({ x = -60, y = 0, relative = true }), { repeating = true })
    hl.bind("l", hl.dsp.window.resize({ x = 60, y = 0, relative = true }), { repeating = true })
    hl.bind("k", hl.dsp.window.resize({ x = 0, y = -60, relative = true }), { repeating = true })
    hl.bind("j", hl.dsp.window.resize({ x = 0, y = 60, relative = true }), { repeating = true })
    hl.bind("escape", hl.dsp.submap("reset"))
    hl.bind("return", hl.dsp.submap("reset"))
end)

hl.bind("SUPER + R", hl.dsp.submap("resize"), { description = "Resize mode" })
