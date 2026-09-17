-- Halcyon — starting the desktop.
--
-- The rule here is that nothing is required. Each service is started if
-- it is installed and skipped if it is not, and the desktop stays usable
-- either way: no Quickshell still leaves you Waybar, no Waybar still
-- leaves you Quickshell, neither still leaves you a working compositor
-- with keybinds.
--
-- Services that ship a systemd user unit are left to systemd when the
-- session is systemd-managed; starting them twice is how you get two
-- notification daemons fighting over the same D-Bus name.

local function have(command)
    -- `command -v` is POSIX and does not fork a shell per candidate the
    -- way `which` does on some systems.
    local pipe = io.popen("command -v " .. command .. " >/dev/null 2>&1 && echo yes", "r")
    if not pipe then
        return false
    end
    local answer = pipe:read("*l")
    pipe:close()
    return answer == "yes"
end

local function systemd_session()
    local pipe = io.popen("systemctl --user is-active hyprland-session.target 2>/dev/null", "r")
    if not pipe then
        return false
    end
    local answer = pipe:read("*l")
    pipe:close()
    return answer == "active"
end

local function start(command, options)
    options = options or {}
    local binary = options.binary or command:match("^(%S+)")
    if options.required ~= false and not have(binary) then
        return false
    end
    hl.exec_cmd(command)
    return true
end

hl.on("hyprland.start", function()
    local managed = systemd_session()

    ---------------------------------------------------------------
    -- Session plumbing
    ---------------------------------------------------------------

    -- Hand the session's environment to systemd and D-Bus so portals,
    -- screen sharing and anything launched outside Hyprland can find the
    -- Wayland display.
    if have("dbus-update-activation-environment") then
        hl.exec_cmd(
            "dbus-update-activation-environment --systemd " ..
            "WAYLAND_DISPLAY XDG_CURRENT_DESKTOP XDG_SESSION_TYPE HYPRLAND_INSTANCE_SIGNATURE"
        )
    end
    if have("systemctl") then
        hl.exec_cmd(
            "systemctl --user import-environment WAYLAND_DISPLAY " ..
            "XDG_CURRENT_DESKTOP HYPRLAND_INSTANCE_SIGNATURE"
        )
    end

    ---------------------------------------------------------------
    -- Authentication and secrets
    ---------------------------------------------------------------

    if not managed then
        if have("hyprpolkitagent") then
            hl.exec_cmd("systemctl --user start hyprpolkitagent 2>/dev/null || hyprpolkitagent")
        elseif have("polkit-kde-authentication-agent-1") then
            hl.exec_cmd("polkit-kde-authentication-agent-1")
        elseif have("lxpolkit") then
            hl.exec_cmd("lxpolkit")
        end
    end

    ---------------------------------------------------------------
    -- Wallpaper
    ---------------------------------------------------------------

    -- `halcyon wallpaper` picks the daemon and restores the last image;
    -- if neither swww nor hyprpaper is installed it does nothing and the
    -- palette's backdrop colour shows through instead.
    if have("halcyon") then
        hl.exec_cmd("halcyon wallpaper current >/dev/null 2>&1 && " ..
                    "halcyon wallpaper set \"$(halcyon wallpaper current)\" >/dev/null 2>&1")
    end

    ---------------------------------------------------------------
    -- The shell
    ---------------------------------------------------------------

    if not managed then
        if have("qs") then
            hl.exec_cmd("qs -c halcyon --daemonize")
        elseif have("quickshell") then
            hl.exec_cmd("quickshell -c halcyon --daemonize")
        end

        if have("waybar") then
            local config = (os.getenv("XDG_CONFIG_HOME") or (os.getenv("HOME") .. "/.config"))
            hl.exec_cmd(
                "waybar -c " .. config .. "/halcyon/generated/waybar-config.jsonc" ..
                " -s " .. config .. "/waybar/style.css"
            )
        end

        if have("hypridle") then
            hl.exec_cmd("hypridle")
        end
    end

    ---------------------------------------------------------------
    -- Optional services
    ---------------------------------------------------------------

    if have("wl-paste") and have("cliphist") then
        -- Two watchers: text and images are stored separately.
        hl.exec_cmd("wl-paste --type text --watch cliphist store")
        hl.exec_cmd("wl-paste --type image --watch cliphist store")
    end

    if not managed and have("halcyon") then
        -- The adaptive power policy. Idle between checks; see
        -- `halcyon power watch`.
        hl.exec_cmd("halcyon power watch")
    end

    ---------------------------------------------------------------
    -- First run
    ---------------------------------------------------------------

    -- If the generated files are missing the desktop still came up, but
    -- it came up plain. Say so once, with the command that fixes it.
    if HALCYON_THEME == nil and have("halcyon") then
        hl.exec_cmd("halcyon theme apply")
    end
end)

hl.on("hyprland.shutdown", function()
    -- Leave no orphaned recording behind; everything else is short-lived
    -- or systemd's to stop.
    if have("halcyon") then
        hl.exec_cmd("halcyon record stop >/dev/null 2>&1 || true")
    end
end)
