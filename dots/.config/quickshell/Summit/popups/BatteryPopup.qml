pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Services.UPower
import qs.common
import qs.services

// The battery, opened from the bar: how full it is and for how long, the power profile (power-profiles-daemon), and
// Halcyon's super battery saver (halcyon saver: 12 fps, dimmer screen, power saver; ~/.local/state/halcyon/saver.json
// while it is on).
PopupWindow {
    id: root
    visible: false
    color: "transparent"
    implicitWidth: 300
    implicitHeight: body.implicitHeight

    readonly property var battery: UPower.displayDevice
    readonly property real level: battery?.percentage ?? 0
    readonly property bool charging: battery?.state === UPowerDeviceState.Charging
    readonly property bool full: battery?.state === UPowerDeviceState.FullyCharged
    readonly property string stateDir: (Quickshell.env("XDG_STATE_HOME") || (Quickshell.env("HOME") + "/.local/state")) + "/halcyon"
    property bool saverOn: false

    function duration(seconds) {
        if (!(seconds > 0))
            return "";
        const h = Math.floor(seconds / 3600), m = Math.round((seconds % 3600) / 60);
        return h > 0 ? `${h} h ${m} min` : `${m} min`;
    }
    readonly property string detail: full ? "Fully charged"
        : charging ? (duration(battery?.timeToFull) !== "" ? `Charging · ${duration(battery.timeToFull)} to full` : "Charging")
        : (duration(battery?.timeToEmpty) !== "" ? `On battery · ${duration(battery.timeToEmpty)} left` : "On battery")

    onVisibleChanged: {
        if (!visible)
            return;
        saverState.reload();
        body.opacity = 0;
        drop.y = -8;
        open.restart();
    }
    ParallelAnimation {
        id: open
        NumberAnimation { target: body; property: "opacity"; to: 1; duration: Theme.animMs + 60; easing.type: Easing.OutCubic }
        NumberAnimation { target: drop; property: "y"; to: 0; duration: Theme.enterMs; easing.type: Easing.OutBack; easing.overshoot: 1.5 }
    }

    // The saver is on while its state file exists.
    FileView {
        id: saverState
        path: root.stateDir + "/saver.json"
        watchChanges: true
        printErrors: false
        onFileChanged: reload()
        onLoaded: root.saverOn = true
        onLoadFailed: root.saverOn = false
    }

    Glass {
        id: body
        transform: Translate { id: drop }
        width: parent.width
        implicitHeight: col.implicitHeight + 32
        radius: Theme.radius + 4
        tint: Theme.glassTint + 0.18

        Column {
            id: col
            x: 16
            y: 16
            width: parent.width - 32
            spacing: 14

            // How full, and for how long.
            Row {
                spacing: 12
                Symbol {
                    anchors.verticalCenter: parent.verticalCenter
                    name: root.charging ? "battery_charging_full" : root.level > 0.8 ? "battery_full" : root.level > 0.5 ? "battery_5_bar"
                        : root.level > 0.2 ? "battery_3_bar" : "battery_alert"
                    size: 30
                    color: !root.charging && root.level <= 0.15 ? "#FF8A80" : Theme.accent
                    fill: 1
                }
                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    Text {
                        text: Math.round(root.level * 100) + "%"
                        color: Theme.text
                        font.family: Theme.font
                        font.pixelSize: 24
                        font.weight: Font.DemiBold
                    }
                    Text {
                        text: root.detail
                        color: Theme.muted
                        font.family: Theme.font
                        font.pixelSize: 12
                    }
                }
            }

            // The power profile.
            Column {
                width: parent.width
                spacing: 8
                Text {
                    text: "Power mode"
                    color: Theme.muted
                    font.family: Theme.font
                    font.pixelSize: 11
                    font.weight: Font.DemiBold
                    font.capitalization: Font.AllUppercase
                }
                Row {
                    width: parent.width
                    spacing: 6
                    Repeater {
                        model: [
                            { profile: PowerProfile.PowerSaver, icon: "eco", label: "Saver" },
                            { profile: PowerProfile.Balanced, icon: "balance", label: "Balanced" },
                            { profile: PowerProfile.Performance, icon: "speed", label: "Performance" }
                        ]
                        delegate: Rectangle {
                            id: mode
                            required property var modelData
                            readonly property bool active: PowerProfiles.profile === modelData.profile
                            readonly property bool available: modelData.profile !== PowerProfile.Performance || PowerProfiles.hasPerformanceProfile
                            width: (parent.width - 12) / 3
                            height: 58
                            radius: 12
                            opacity: available ? 1 : 0.4
                            color: active ? Theme.alpha(Theme.accent, 0.24) : modeArea.containsMouse ? Theme.alpha(Theme.text, 0.10) : Theme.alpha(Theme.text, 0.05)
                            Behavior on color { ColorAnimation { duration: Theme.animMs } }
                            scale: modeArea.pressed ? 0.95 : 1
                            Behavior on scale { SpringAnimation { spring: Theme.springStiffness * 1.6; damping: Theme.springDamping; epsilon: 0.002 } }
                            Column {
                                anchors.centerIn: parent
                                spacing: 2
                                Symbol {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    name: mode.modelData.icon
                                    fill: mode.active ? 1 : 0
                                    color: mode.active ? Theme.accent : Theme.text
                                }
                                Text {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    text: mode.modelData.label
                                    color: mode.active ? Theme.accent : Theme.text
                                    font.family: Theme.font
                                    font.pixelSize: 11
                                }
                            }
                            MouseArea {
                                id: modeArea
                                anchors.fill: parent
                                hoverEnabled: true
                                enabled: mode.available
                                cursorShape: Qt.PointingHandCursor
                                onClicked: PowerProfiles.profile = mode.modelData.profile
                            }
                        }
                    }
                }
            }

            // The super battery saver.
            Rectangle {
                width: parent.width
                height: 48
                radius: 12
                color: saverArea.containsMouse ? Theme.alpha(Theme.text, 0.10) : Theme.alpha(Theme.text, 0.05)
                Behavior on color { ColorAnimation { duration: Theme.animMs } }
                Symbol {
                    x: 12
                    anchors.verticalCenter: parent.verticalCenter
                    name: "bolt"
                    fill: root.saverOn ? 1 : 0
                    color: root.saverOn ? Theme.warm : Theme.text
                }
                Column {
                    x: 44
                    anchors.verticalCenter: parent.verticalCenter
                    Text {
                        text: "Super battery saver"
                        color: Theme.text
                        font.family: Theme.font
                        font.pixelSize: 13
                    }
                    Text {
                        text: "12 fps, dimmer screen, power saver"
                        color: Theme.muted
                        font.family: Theme.font
                        font.pixelSize: 11
                    }
                }
                // The switch.
                Rectangle {
                    anchors { right: parent.right; rightMargin: 12; verticalCenter: parent.verticalCenter }
                    width: 38
                    height: 22
                    radius: 11
                    color: root.saverOn ? Theme.accent : Theme.alpha(Theme.text, 0.22)
                    Behavior on color { ColorAnimation { duration: Theme.animMs } }
                    Rectangle {
                        width: 16
                        height: 16
                        radius: 8
                        y: 3
                        x: root.saverOn ? parent.width - width - 3 : 3
                        color: root.saverOn ? Theme.accentText : Theme.text
                        Behavior on x { SpringAnimation { spring: Theme.springStiffness * 1.5; damping: Theme.springDamping; epsilon: 0.2 } }
                    }
                }
                MouseArea {
                    id: saverArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        root.saverOn = !root.saverOn;   // at once; the state file confirms it
                        Quickshell.execDetached([Actions.halcyon + "/halcyon_saver.py", "toggle"]);
                    }
                }
            }
        }
    }
}
