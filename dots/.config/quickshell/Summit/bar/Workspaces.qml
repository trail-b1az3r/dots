pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Hyprland
import qs.common

// This monitor's workspaces as dots; the active one stretches into a pill in the accent. Click to go, scroll to step.
Row {
    id: root
    required property var screen
    readonly property HyprlandMonitor monitor: Hyprland.monitorFor(root.screen)
    readonly property int activeId: monitor?.activeWorkspace?.id ?? 1
    // Workspaces 1..max(5, highest in use on this monitor), so empty ones are there to click.
    readonly property var ids: {
        const used = Hyprland.workspaces.values.filter(w => w.id > 0 && w.monitor?.name === root.monitor?.name).map(w => w.id);
        const top = Math.max(5, root.activeId, ...used);
        return Array.from({ length: top }, (_, i) => i + 1);
    }
    readonly property var occupied: Hyprland.workspaces.values.filter(w => (w.toplevels?.values?.length ?? 0) > 0).map(w => w.id)
    spacing: 6
    leftPadding: 6
    rightPadding: 6

    Repeater {
        model: root.ids
        delegate: Rectangle {
            id: dot
            required property int modelData
            readonly property bool active: modelData === root.activeId
            readonly property bool used: root.occupied.includes(modelData)
            anchors.verticalCenter: parent.verticalCenter
            width: active ? 26 : 8
            height: 8
            radius: 4
            color: active ? Theme.accent : used ? Theme.alpha(Theme.text, 0.55) : Theme.alpha(Theme.text, 0.2)
            // The active dot stretches with a spring; a hovered one swells.
            Behavior on width { SpringAnimation { spring: Theme.springStiffness; damping: Theme.springDamping; epsilon: 0.2 } }
            Behavior on color { ColorAnimation { duration: Theme.animMs } }
            scale: hover.containsMouse && !active ? 1.35 : 1
            Behavior on scale { NumberAnimation { duration: Theme.animMs; easing.type: Easing.OutBack } }
            MouseArea {
                id: hover
                anchors.fill: parent
                anchors.margins: -6
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: Hyprland.dispatch(`hl.dsp.focus({ workspace = ${dot.modelData} })`)
            }
        }
    }

    WheelHandler {
        onWheel: event => Hyprland.dispatch(`hl.dsp.focus({ workspace = "r${event.angleDelta.y > 0 ? "-" : "+"}1" })`)
    }
}
