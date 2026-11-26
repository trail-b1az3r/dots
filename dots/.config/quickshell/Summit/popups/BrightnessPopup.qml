pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import qs.common
import qs.services

// The brightness slider, under the bar's left group: the Halcyon shell's (common/Slider.qml), backlight above the sun
// and the dimmer gamma below it (services/Brightness.qml). The sun button opens it; scrolling the button (or the
// launcher) changes the brightness and shows it here, and it goes again a moment after the last change unless the
// pointer is on it.
PopupWindow {
    id: root
    required property var screen
    readonly property var monitor: Brightness.forScreen(root.screen)
    readonly property real level: Brightness.value(root.monitor)
    visible: false
    color: "transparent"
    implicitWidth: 300
    implicitHeight: body.implicitHeight + 8

    // Opened by a click: stays until clicked again. Shown by a scroll: goes by itself.
    property bool pinned: false
    function peek() {
        if (!root.visible) {
            root.pinned = false;
            root.visible = true;
        }
        if (!root.pinned)
            away.restart();
    }
    function toggle() {
        root.pinned = !root.visible || !root.pinned;
        root.visible = root.pinned;
    }
    Timer {
        id: away
        interval: 1600
        onTriggered: if (!root.pinned && !hover.hovered && !slider.dragging) root.visible = false
    }

    onVisibleChanged: {
        if (!visible)
            return;
        body.opacity = 0;
        drop.y = -8;
        open.restart();
    }
    ParallelAnimation {
        id: open
        NumberAnimation { target: body; property: "opacity"; to: 1; duration: Theme.animMs + 60; easing.type: Easing.OutCubic }
        NumberAnimation { target: drop; property: "y"; to: 0; duration: Theme.enterMs; easing.type: Easing.OutBack; easing.overshoot: 1.5 }
    }

    Glass {
        id: body
        transform: Translate { id: drop }
        width: parent.width
        implicitHeight: col.implicitHeight + 28
        radius: Theme.radius + 4
        tint: Theme.glassTint + 0.18
        HoverHandler {
            id: hover
            onHoveredChanged: if (!hovered) away.restart()
        }

        Column {
            id: col
            x: 14
            y: 14
            width: parent.width - 28
            spacing: 12
            Row {
                width: parent.width
                Text {
                    width: parent.width - levelText.implicitWidth
                    text: "Brightness"
                    color: Theme.text
                    font.family: Theme.font
                    font.pixelSize: 14
                    font.weight: Font.DemiBold
                }
                Text {
                    id: levelText
                    text: root.monitor?.available && Brightness.gamma === 100 ? Math.round((root.monitor?.brightness ?? 0) * 100) + "%"
                        : "Dimmed " + Brightness.gamma + "%"
                    color: Theme.muted
                    font.family: Theme.font
                    font.pixelSize: 12
                }
            }
            Slider {
                id: slider
                width: parent.width
                icon: "light_mode"
                markIcon: root.monitor?.available ? "wb_twilight" : ""
                markAt: Brightness.split
                value: root.level
                valueText: levelText.text
                onMoved: v => {
                    Brightness.setValue(root.monitor, v);
                    away.restart();
                }
            }
        }
    }
}
