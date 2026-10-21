pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Io
import qs
import qs.services
import qs.modules.common

/**
 * Rests the animated wallpaper (mpvpaper) while nobody can see it: the screen is locked, or every monitor has a
 * fullscreen window over it. A stopped mpvpaper keeps its place and its memory, and carries on from the same frame.
 * Settings > Background > Pause the animated wallpaper turns it off.
 */
Scope {
    id: root

    readonly property bool enabled: Config.options?.background.pauseVideoWhenHidden ?? true
    readonly property bool coveredEverywhere: {
        const screens = Quickshell.screens;
        return screens.length > 0 && screens.every(screen => HyprlandData.compositorFullscreenOnMonitor(screen.name));
    }
    readonly property bool asleep: enabled && (GlobalStates.screenLocked || coveredEverywhere)

    // Wait a moment before resting it, so switching in and out of a fullscreen window does not flicker the wallpaper.
    property bool resting: false
    onAsleepChanged: asleep ? rest.restart() : wake()
    Timer {
        id: rest
        interval: 1500
        onTriggered: {
            root.resting = true;
            signal.command = ["pkill", "-STOP", "-x", "mpvpaper"];
            signal.running = true;
        }
    }
    function wake() {
        rest.stop();
        if (!resting)
            return;
        resting = false;
        signal.command = ["pkill", "-CONT", "-x", "mpvpaper"];
        signal.running = true;
    }
    // Turning the setting off must not leave it stopped.
    onEnabledChanged: if (!enabled) wake()

    Process {
        id: signal
    }
}
