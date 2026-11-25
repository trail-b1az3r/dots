pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Hyprland
import qs.common
import qs.services

// Hypr mode (halcyon/modes.lua, keys in halcyon/hypr_mode.lua): while Hyprland's "hypr" submap is on, a card of frosted
// glass above the dock shows the mode's keys, which then work without Super. It rises in when the mode starts and
// sinks away when it ends (Esc, the toggle again, or a few idle seconds). Clicks go through to the windows.
Scope {
    id: root

    readonly property string modeName: "hypr"
    property bool active: false
    property bool shown: false
    property var binds: []

    // "Hypr mode: Move window left" -> "Move window left"; the keys as chips.
    function keysOf(bind) {
        const keys = [];
        const mask = bind.modmask ?? 0;
        if (mask & (1 << 6)) keys.push("Super");
        if (mask & (1 << 2)) keys.push("Ctrl");
        if (mask & (1 << 3)) keys.push("Alt");
        if (mask & (1 << 0)) keys.push("Shift");
        const symbols = { "Left": "←", "Right": "→", "Up": "↑", "Down": "↓", "Return": "Enter", "Escape": "Esc" };
        keys.push(symbols[bind.key] ?? bind.key);
        return keys;
    }

    Connections {
        target: Hyprland
        function onRawEvent(event) {
            if (event.name !== "submap")
                return;
            const entered = event.data === root.modeName;
            if (entered === root.active)
                return;
            root.active = entered;
            if (entered) {
                hide.stop();
                bindsProc.running = true;   // the keys as they are now (hypr_mode.lua may have changed)
                root.shown = true;
            } else {
                hide.restart();
            }
        }
    }

    Process {
        id: bindsProc
        command: ["hyprctl", "binds", "-j"]
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    root.binds = JSON.parse(text).filter(b => (b.submap === root.modeName || (b.description ?? "").startsWith("Hypr mode:"))
                                                         && (b.description ?? "").length > 0
                                                         && !(b.description ?? "").includes("Toggle hypr mode"));
                } catch (e) {
                    root.binds = [];
                }
            }
        }
    }

    Timer {
        id: hide
        interval: Theme.animMs + 120
        onTriggered: root.shown = false
    }

    LazyLoader {
        active: root.shown

        PanelWindow {
            id: panel
            screen: Quickshell.screens.find(s => s.name === Hyprland.focusedMonitor?.name) ?? Quickshell.screens[0]
            color: "transparent"
            WlrLayershell.namespace: "summit-hyprmode"
            WlrLayershell.layer: WlrLayer.Overlay
            exclusionMode: ExclusionMode.Ignore
            anchors.bottom: true
            margins.bottom: 54 + Theme.gap * 3
            implicitWidth: Math.min(card.implicitWidth, (screen?.width ?? 1400) - 80)
            implicitHeight: card.implicitHeight + 16
            // Clicks pass through: the card only shows.
            mask: Region {}

            Glass {
                id: card
                tint: Theme.glassTint + 0.22
                radius: Theme.radius + 6
                width: parent.width
                implicitWidth: Math.max(header.implicitWidth, grid.implicitWidth) + 40
                implicitHeight: header.implicitHeight + grid.implicitHeight + 50
                y: root.active ? 0 : 24
                opacity: root.active ? 1 : 0
                scale: root.active ? 1 : 0.96
                Behavior on y { NumberAnimation { duration: Theme.enterMs; easing.type: Easing.OutBack; easing.overshoot: 1.3 } }
                Behavior on opacity { NumberAnimation { duration: Theme.animMs + 40; easing.type: Easing.OutCubic } }
                Behavior on scale { NumberAnimation { duration: Theme.enterMs; easing.type: Easing.OutCubic } }

                Row {
                    id: header
                    x: 20
                    y: 16
                    spacing: 10
                    Symbol {
                        anchors.verticalCenter: parent.verticalCenter
                        name: "keyboard"
                        size: 22
                        color: Theme.accent
                        fill: 1
                    }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "Hypr mode"
                        color: Theme.text
                        font.family: Theme.font
                        font.pixelSize: 16
                        font.weight: Font.DemiBold
                    }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "keys work without Super  ·  Esc leaves"
                        color: Theme.muted
                        font.family: Theme.font
                        font.pixelSize: 12
                    }
                }

                Grid {
                    id: grid
                    x: 20
                    anchors.top: header.bottom
                    anchors.topMargin: 14
                    columns: Math.max(1, Math.min(3, Math.ceil(root.binds.length / 6)))
                    columnSpacing: 26
                    rowSpacing: 8
                    flow: Grid.TopToBottom
                    rows: Math.ceil(root.binds.length / columns)

                    Text {
                        visible: root.binds.length === 0
                        text: "No keys in this mode: add them in ~/.config/hypr/custom/hypr_mode.lua"
                        color: Theme.muted
                        font.family: Theme.font
                        font.pixelSize: 12
                    }

                    Repeater {
                        model: root.binds
                        delegate: Row {
                            id: entry
                            required property var modelData
                            spacing: 10
                            Row {
                                spacing: 4
                                anchors.verticalCenter: parent.verticalCenter
                                Repeater {
                                    model: root.keysOf(entry.modelData)
                                    delegate: Rectangle {
                                        required property string modelData
                                        width: Math.max(24, label.implicitWidth + 12)
                                        height: 24
                                        radius: 7
                                        color: Theme.alpha(Theme.text, 0.10)
                                        Text {
                                            id: label
                                            anchors.centerIn: parent
                                            text: parent.modelData
                                            color: Theme.text
                                            font.family: Theme.font
                                            font.pixelSize: 12
                                            font.weight: Font.Medium
                                        }
                                    }
                                }
                            }
                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: (entry.modelData.description ?? "").replace(/^Hypr mode:\s*/, "")
                                color: Theme.muted
                                font.family: Theme.font
                                font.pixelSize: 13
                            }
                        }
                    }
                }
            }
        }
    }
}
