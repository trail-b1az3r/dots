//@ pragma UseQApplication
//@ pragma Env QT_QUICK_CONTROLS_STYLE=Basic

// Summit: Halcyon's clean shell (HyperNeo v2). A top bar of three floating groups, a bottom bar of apps, the
// wallpaper, and nothing else on screen: menus are rofi (Halcyon's config), the forecast is its own window, and
// the theme picker is a pane of frosted glass. Everything is frosted glass: Hyprland blurs behind each layer.
// Started by halcyon-summit.service when the active theme's desktop_shell is "Summit" (halcyon/desktop-shell).

import QtQuick
import Quickshell
import Quickshell.Io
import qs.bar
import qs.dock
import qs.popups
import qs.services

ShellRoot {
    Variants {
        model: Quickshell.screens
        delegate: Background {}
    }
    Variants {
        model: Quickshell.screens
        delegate: TopBar {}
    }
    Variants {
        model: Quickshell.screens
        delegate: Dock {}
    }

    ThemePicker {
        id: themePicker
    }

    // The power button opens the power menu instead of switching off: hold logind's power-key lock while Summit
    // runs (Hyprland binds the key to `desktop-shell power-menu`). It goes with Summit.
    Process {
        running: !Quickshell.env("SUMMIT_NO_POWER_KEY")
        command: ["systemd-inhibit", "--what=handle-power-key", "--who=Summit", "--mode=block",
            "--why=The power button opens the power menu", "sleep", "infinity"]
    }

    IpcHandler {
        target: "summit"
        function launcher(): void { Actions.launcher(); }
        function power(): void { Actions.power(); }
        function windows(): void { Actions.windows(); }
        function themes(): void { themePicker.toggle(); }
        function keys(): void { Actions.keys(); }
    }
}
