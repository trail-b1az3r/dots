-- put former exec-once commands inside the func and former exec commands outside
hl.on("hyprland.start", function ()

    -- Bar, wallpaper
    hl.exec_cmd("$HOME/.config/hypr/hyprland/scripts/start_geoclue_agent.sh")
    -- Quickshell is started by the halcyon-quickshell user service (see halcyon/init.lua).
    hl.exec_cmd("$HOME/.config/hypr/custom/scripts/__restore_video_wallpaper.sh")

    -- Core components (authentication, lock screen, notification daemon)
    hl.exec_cmd("gnome-keyring-daemon --start --components=secrets")
    hl.exec_cmd("hypridle")
    hl.exec_cmd("dbus-update-activation-environment --all")
    hl.exec_cmd("sleep 1 && dbus-update-activation-environment --systemd WAYLAND_DISPLAY XDG_CURRENT_DESKTOP") -- Some fix idk

    -- Audio. EasyEffects only when turned on (halcyon audio easyeffects on, or Settings > Halcyon > Sound): it puts
    -- its own output and microphone in front of the real ones, which broke headphones and webcam microphones.
    hl.exec_cmd("[ -e \"${XDG_STATE_HOME:-$HOME/.local/state}/halcyon/easyeffects\" ] && easyeffects --hide-window --service-mode")

    -- Clipboard: history
    --hl.exec_cmd("wl-paste --watch cliphist store")
    hl.exec_cmd("wl-paste --type text --watch bash -c 'cliphist store && qs -c $qsConfig ipc call cliphistService update'")
    hl.exec_cmd("wl-paste --type image --watch bash -c 'cliphist store && qs -c $qsConfig ipc call cliphistService update'")

    -- Cursor
    hl.exec_cmd("hyprctl setcursor Bibata-Modern-Classic 24")

    -- Razer devices. OpenRazer's daemon is a user service that nothing else starts, so it is started at login,
    -- before the Polychromatic tray applet, which needs it. Both are skipped when they are not installed.
    hl.exec_cmd("systemctl --user start openrazer-daemon.service >/dev/null 2>&1; " ..
        "command -v polychromatic-tray-applet >/dev/null && polychromatic-tray-applet")
end)
