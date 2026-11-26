pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Hyprland

/**
 * Whether hypr mode is on: Hyprland's "hypr" submap (halcyon/modes.lua). The card of its keys (popups/HyprMode.qml),
 * the glow round the screens (popups/HyprFrame.qml) and the chip on the bar follow it.
 */
Singleton {
    id: root

    readonly property string name: "hypr"
    property bool active: false
    // One more every time the mode starts, so what animates on it can start again.
    property int entries: 0

    function set(on) {
        if (on === root.active)
            return;
        root.active = on;
        if (on)
            root.entries++;
    }

    Connections {
        target: Hyprland
        function onRawEvent(event) {
            if (event.name === "submap")
                root.set(event.data === root.name);
        }
    }

    // Summit (re)started while the mode was on.
    Process {
        running: true
        command: ["hyprctl", "submap"]
        stdout: StdioCollector {
            onStreamFinished: root.set(text.trim() === root.name)
        }
    }
}
