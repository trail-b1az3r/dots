pragma Singleton

import QtQuick
import Quickshell

/**
 * What Summit's buttons do. The launcher, window switcher, clipboard and power menu are rofi with Halcyon's config
 * (~/.config/rofi, coloured by the active theme); the forecast is halcyon-weather's window when it is installed.
 */
Singleton {
    id: root

    readonly property string halcyon: Quickshell.env("HOME") + "/.config/hypr/hyprland/halcyon"
    readonly property string rofiScript: halcyon + "/summit/rofi-menu"

    function launcher() { Quickshell.execDetached([root.rofiScript, "apps"]); }
    function windows() { Quickshell.execDetached([root.rofiScript, "windows"]); }
    function clipboard() { Quickshell.execDetached([root.rofiScript, "clipboard"]); }
    function power() { Quickshell.execDetached([root.rofiScript, "power"]); }
    // The theme picker is Summit's own (popups/ThemePicker.qml), listening for this.
    signal themesRequested
    function themes() { root.themesRequested(); }
    function keys() { Quickshell.execDetached([root.rofiScript, "keys"]); }
    function forecast() { Quickshell.execDetached([root.rofiScript, "forecast"]); }
    function run(command) { Quickshell.execDetached(["sh", "-c", command]); }
}
