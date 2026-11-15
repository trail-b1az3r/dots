pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Shapes
import qs.modules.common

/**
 * How far along something is (0 to 1), as a line drawn the theme's way (ThemeLook.spec.progress): a plain line, a
 * lit line with its glow, facets, a thick pill, a fine rail with a diamond on it, a row of keys, or Sword Art
 * Online's slanted HP bar.
 */
Item {
    id: bar

    property real value: 0
    property color accent: look.accentA
    property ThemeLook look: ThemeLook {}

    readonly property real level: Math.max(0, Math.min(1, value))
    readonly property string kind: look.spec.progress
    readonly property int cells: kind === "segments" ? 16 : 12

    implicitHeight: kind === "hp" ? 10 : kind === "pill" ? 8 : kind === "blocks" ? 12 : kind === "segments" ? 7 : kind === "rail" ? 12 : 5
    implicitWidth: 200

    function tint(alpha) {
        return Qt.rgba(accent.r, accent.g, accent.b, alpha);
    }

    // line, pill and glow: a track and its fill
    Rectangle {
        visible: bar.kind === "line" || bar.kind === "pill" || bar.kind === "glow"
        anchors.verticalCenter: parent.verticalCenter
        width: parent.width
        height: bar.kind === "glow" ? 2 : parent.height
        radius: height / 2
        color: bar.tint(bar.kind === "glow" ? 0.25 : 0.18)

        // glow: the light round the lit part
        Rectangle {
            visible: bar.kind === "glow"
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width * bar.level + 6
            x: -3
            height: 9
            radius: 4.5
            color: bar.tint(0.22)
        }
        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            width: Math.max(parent.height, parent.width * bar.level)
            height: parent.height
            radius: parent.radius
            color: bar.accent
            visible: bar.level > 0
        }
    }

    // segments and blocks: a row of cells, lit up to the value
    Row {
        visible: bar.kind === "segments" || bar.kind === "blocks"
        anchors.fill: parent
        spacing: bar.kind === "blocks" ? 4 : 3
        Repeater {
            model: (bar.kind === "segments" || bar.kind === "blocks") ? bar.cells : 0
            delegate: Rectangle {
                required property int index
                readonly property bool lit: index < Math.round(bar.level * bar.cells)
                width: (bar.width - (bar.cells - 1) * parent.spacing) / bar.cells
                height: bar.height
                radius: bar.kind === "blocks" ? 3 : 0
                color: lit ? bar.accent : bar.tint(0.16)
                border.width: bar.kind === "blocks" ? 1.5 : 0
                border.color: Qt.darker(bar.look.card, 2.4)
            }
        }
    }

    // hp: the game's HP bar, square at the start and cut on a slant at the end, a light along the top of its fill
    Item {
        id: hp
        visible: bar.kind === "hp"
        anchors.fill: parent
        readonly property real slant: height * 0.7
        Shape {
            anchors.fill: parent
            ShapePath {
                strokeWidth: 1
                strokeColor: bar.look.edge
                fillColor: Qt.rgba(bar.look.text.r, bar.look.text.g, bar.look.text.b, 0.14)
                PathSvg { path: `M 0 0 L ${bar.width} 0 L ${bar.width - hp.slant} ${bar.height} L 0 ${bar.height} Z` }
            }
        }
        Rectangle {
            x: 2
            y: 2
            width: Math.max(0, (bar.width - hp.slant - 4) * bar.level)
            height: bar.height - 4
            color: bar.accent
            Rectangle { width: parent.width; height: Math.max(1, parent.height / 3); color: Qt.rgba(1, 1, 1, 0.4) }
        }
    }

    // rail: a fine line and a diamond where it has got to
    Rectangle {
        visible: bar.kind === "rail"
        anchors.verticalCenter: parent.verticalCenter
        width: parent.width
        height: 1.5
        color: bar.tint(0.35)
        Rectangle {
            width: parent.width * bar.level
            height: parent.height
            color: bar.accent
        }
    }
    Rectangle {
        visible: bar.kind === "rail"
        x: bar.width * bar.level - width / 2
        anchors.verticalCenter: parent.verticalCenter
        width: 8
        height: 8
        rotation: 45
        color: bar.accent
    }
}
