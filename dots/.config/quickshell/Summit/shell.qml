//@ pragma UseQApplication
//@ pragma Env QT_QUICK_CONTROLS_STYLE=Basic

// Summit: Halcyon's clean shell (HyperNeo v2). A top bar of three floating groups, a bottom bar of apps, the
// wallpaper, and a side menu down the right (the Halcyon shell's sidebar: sliders, quick toggles, notifications, the
// calendar, to-do list and timer). Menus are rofi (Halcyon's config), the forecast is its own window, and the theme
// picker is a pane of frosted glass. Everything is frosted glass: Hyprland blurs behind each layer. Summit is the
// notification server while it runs; important notifications (a tiny local model) open under the clock.
// Started by halcyon-summit.service when the active theme's desktop_shell is "Summit" (halcyon/desktop-shell).

import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Hyprland
import qs.common
import qs.bar
import qs.dock
import qs.popups
import qs.services
import qs.side

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

    // Hypr mode's keys, while it is on (Super+Ctrl+H), and its glow round every screen.
    HyprMode {}
    Variants {
        model: Quickshell.screens
        delegate: HyprFrame {}
    }

    // The keys cheat sheet (Super+/, Super+Shift+/ the hypr keys).
    Cheatsheet {
        id: cheatsheet
    }
    Connections {
        target: Actions
        function onKeysRequested(page) { cheatsheet.toggle(page); }
    }

    // The side menu, and the right edge of the rightmost screen that opens it.
    SideMenu {}
    EdgeTrigger {}

    // Notifications: popups in the corner, important ones under the clock. Summit takes the notification bus at once.
    NotificationPopups {}
    ImportantBanner {}
    Component.onCompleted: Notifs.count

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
        function keys(): void { cheatsheet.toggle("all"); }
        function hyprkeys(): void { cheatsheet.toggle("hypr"); }
        // The side menu on the focused screen.
        function sideMenu(): void { SummitState.toggleSideMenu(Quickshell.screens.find(s => s.name === Hyprland.focusedMonitor?.name) ?? Quickshell.screens[0]); }
        // RightFont everywhere, until Summit restarts (halcyon fonts right-font).
        function rightFont(on: bool): void { Theme.rightFont = on; }
    }
}
