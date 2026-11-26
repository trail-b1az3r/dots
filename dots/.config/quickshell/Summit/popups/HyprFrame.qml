pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.common
import qs.services

// Hypr mode on a screen: a glow in the accent traces round its edges when the mode starts (out from the top centre,
// down the sides, closing at the bottom), breathes while it is on, and draws back the way it came when it ends.
// Clicks go through; the layer exists only while it shows. Settings > Summit > Hypr mode turns it off.
Scope {
    id: root
    required property var modelData

    // 0 nothing .. 1 the whole frame.
    property real progress: 0
    readonly property bool wanted: HyprModeState.active && Prefs.hyprModeGlow

    onWantedChanged: {
        if (wanted) {
            close.stop();
            open.restart();
        } else {
            open.stop();
            close.restart();
        }
    }
    NumberAnimation {
        id: open
        target: root
        property: "progress"
        to: 1
        duration: 760
        easing.type: Easing.OutCubic
    }
    NumberAnimation {
        id: close
        target: root
        property: "progress"
        to: 0
        duration: 420
        easing.type: Easing.InCubic
    }

    LazyLoader {
        active: root.progress > 0 || root.wanted

        PanelWindow {
            id: frame
            screen: root.modelData
            color: "transparent"
            WlrLayershell.namespace: "summit-hyprframe"
            WlrLayershell.layer: WlrLayer.Overlay
            exclusionMode: ExclusionMode.Ignore
            anchors { top: true; bottom: true; left: true; right: true }
            mask: Region {}

            readonly property real p: root.progress
            function part(from, to) { return Math.max(0, Math.min(1, (frame.p - from) / (to - from))); }
            readonly property real top: part(0, 0.38)
            readonly property real sides: part(0.28, 0.72)
            readonly property real bottom: part(0.62, 1)
            readonly property int thick: 22
            readonly property color glow: Theme.accent

            Item {
                id: edges
                anchors.fill: parent
                // Breathing, while the mode is on and the frame is whole.
                opacity: 1
                SequentialAnimation on opacity {
                    running: root.wanted && frame.p >= 1
                    loops: Animation.Infinite
                    alwaysRunToEnd: true
                    NumberAnimation { to: 0.55; duration: 1400; easing.type: Easing.InOutSine }
                    NumberAnimation { to: 1; duration: 1400; easing.type: Easing.InOutSine }
                }

                // Top: out from the centre both ways.
                Edge { x: parent.width / 2 * (1 - frame.top); y: 0; width: parent.width / 2 * frame.top; height: frame.thick; vertical: false; from: 0 }
                Edge { x: parent.width / 2; y: 0; width: parent.width / 2 * frame.top; height: frame.thick; vertical: false; from: 0 }
                // Sides: down from the top corners.
                Edge { x: 0; y: 0; width: frame.thick; height: parent.height * frame.sides; vertical: true; from: 0 }
                Edge { x: parent.width - frame.thick; y: 0; width: frame.thick; height: parent.height * frame.sides; vertical: true; from: 1 }
                // Bottom: in from both corners, meeting in the middle.
                Edge { x: 0; y: parent.height - frame.thick; width: parent.width / 2 * frame.bottom; height: frame.thick; vertical: false; from: 1 }
                Edge { x: parent.width - width; y: parent.height - frame.thick; width: parent.width / 2 * frame.bottom; height: frame.thick; vertical: false; from: 1 }
            }

            // A strip of glow along an edge: bright at the screen's edge (`from` 0: top or left; 1: bottom or right),
            // fading inwards, with a thin bright line on the edge itself.
            component Edge: Item {
                id: edge
                property bool vertical
                property int from
                visible: width > 0.5 && height > 0.5
                Rectangle {
                    anchors.fill: parent
                    gradient: Gradient {
                        orientation: edge.vertical ? Gradient.Horizontal : Gradient.Vertical
                        GradientStop { position: 0; color: Theme.alpha(frame.glow, edge.from === 0 ? 0.55 : 0) }
                        GradientStop { position: 1; color: Theme.alpha(frame.glow, edge.from === 0 ? 0 : 0.55) }
                    }
                }
                Rectangle {
                    color: Theme.alpha(frame.glow, 0.95)
                    x: edge.vertical ? (edge.from === 0 ? 0 : parent.width - 2) : 0
                    y: edge.vertical ? 0 : (edge.from === 0 ? 0 : parent.height - 2)
                    width: edge.vertical ? 2 : parent.width
                    height: edge.vertical ? parent.height : 2
                }
            }
        }
    }
}
