pragma Singleton
pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Io

/**
 * What Summit is doing right now: the side menu (open, on which screen), and the quick toggles that are Summit's own
 * (keep awake, night light, game mode). Nothing here outlives Summit except game mode, whose file Hyprland reads.
 */
Singleton {
    id: root

    property bool sideMenuOpen: false
    property var sideMenuScreen: null
    // The side menu's page: "" (the main one), "wifi", "bluetooth" or "sound".
    property string sideMenuPage: ""

    function openSideMenu(screen) {
        root.sideMenuScreen = screen;
        root.sideMenuPage = "";
        root.sideMenuOpen = true;
    }
    function toggleSideMenu(screen) {
        if (root.sideMenuOpen && root.sideMenuScreen === screen)
            root.sideMenuOpen = false;
        else
            root.openSideMenu(screen);
    }

    // The side menu's focus timer (side/TimerView.qml): here, so it runs on with the menu closed.
    property int timerLength: 25 * 60
    property int timerLeft: timerLength
    property bool timerRunning: false
    function formatTime(seconds) {
        const m = Math.floor(seconds / 60), s = seconds % 60;
        return (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s;
    }
    Timer {
        interval: 1000
        repeat: true
        running: root.timerRunning
        onTriggered: {
            root.timerLeft = Math.max(0, root.timerLeft - 1);
            if (root.timerLeft === 0) {
                root.timerRunning = false;
                Quickshell.execDetached(["notify-send", "-a", "Summit", "-u", "critical", "Time's up",
                    root.formatTime(root.timerLength) + " are over."]);
            }
        }
    }

    // Keep awake: the screen does not dim, lock or sleep (an idle inhibitor on the bar, bar/TopBar.qml).
    property bool keepAwake: false

    // Night light: hyprsunset's colour temperature (the brightness slider uses its gamma).
    property bool nightLight: false
    readonly property int nightTemperature: 4500
    onNightLightChanged: Quickshell.execDetached(["sh", "-c",
        "pidof hyprsunset >/dev/null || { hyprsunset >/dev/null 2>&1 & sleep 0.5; }; hyprctl hyprsunset temperature "
        + (root.nightLight ? root.nightTemperature : 6500)])

    // Game mode: no animations, blur, shadows, gaps or rounding, and tearing allowed (halcyon/gamemode.lua, read while
    // ~/.local/state/halcyon/gamemode.json exists; Hyprland reloads to apply it).
    readonly property string stateDir: (Quickshell.env("XDG_STATE_HOME") || (Quickshell.env("HOME") + "/.local/state")) + "/halcyon"
    property bool gameMode: false
    function setGameMode(on) {
        root.gameMode = on;
        Quickshell.execDetached(["sh", "-c", (on ? "mkdir -p \"$1\" && echo '{}' > \"$1/gamemode.json\"" : "rm -f \"$1/gamemode.json\"")
            + " && hyprctl reload >/dev/null", "sh", root.stateDir]);
    }
    FileView {
        path: root.stateDir + "/gamemode.json"
        watchChanges: true
        printErrors: false
        onFileChanged: reload()
        onLoaded: root.gameMode = true
        onLoadFailed: root.gameMode = false
    }
}
