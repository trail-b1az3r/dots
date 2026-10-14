pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Shapes

/**
 * The sun dial's drawing: today's arc from sunrise (left) to sunset (right) over a horizon line, with the sun on it.
 * Before sunrise and after sunset the sun sits just under the horizon, dimmed. Without a location (progress
 * undefined) only a faint arc is drawn.
 *
 * Needs only QtQuick, so it can be drawn and tested on its own.
 */
Item {
    id: arc

    /** 0 at sunrise, 1 at sunset; below 0 before dawn, above 1 after dusk; undefined when unknown. */
    property var progress: undefined
    property color colLine: "#80ffffff"
    property color colSun: "#ffc18a"
    property color colGlow: "#ff4940"
    /** Red Sun: the sun is a ring, like the one in the wallpaper. */
    property bool ring: false

    readonly property bool known: progress !== undefined && progress !== null && !isNaN(progress)
    readonly property bool daytime: known && progress >= 0 && progress <= 1
    readonly property real t: known ? Math.max(0, Math.min(1, progress)) : 0.5
    readonly property real cx: width / 2
    readonly property real baseY: height - 4
    readonly property real r: Math.min(width / 2 - 3, height - 7)
    // The sun on the arc by day; at night it rests under the horizon at the end it set (or will rise).
    readonly property real sunX: daytime ? cx - r * Math.cos(Math.PI * t) : (known && progress < 0 ? cx - r : cx + r)
    readonly property real sunY: daytime ? baseY - r * Math.sin(Math.PI * t) : baseY + 2

    implicitWidth: 34
    implicitHeight: 22

    layer.enabled: true
    layer.samples: 4

    Shape {
        anchors.fill: parent
        // The horizon.
        ShapePath {
            strokeWidth: 1
            strokeColor: arc.colLine
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            startX: 1; startY: arc.baseY
            PathLine { x: arc.width - 1; y: arc.baseY }
        }
        // The rest of the day, dotted.
        ShapePath {
            strokeWidth: 1.2
            strokeColor: arc.colLine
            strokeStyle: ShapePath.DashLine
            dashPattern: [1.5, 2.5]
            fillColor: "transparent"
            startX: arc.cx - arc.r; startY: arc.baseY
            PathArc { x: arc.cx + arc.r; y: arc.baseY; radiusX: arc.r; radiusY: arc.r }
        }
        // The part of the day already gone, solid.
        ShapePath {
            strokeWidth: 1.6
            strokeColor: arc.daytime ? arc.colSun : "transparent"
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            startX: arc.cx - arc.r; startY: arc.baseY
            PathArc { x: arc.sunX; y: arc.sunY; radiusX: arc.r; radiusY: arc.r }
        }
    }

    // The sun: a glow, then the disc (or ring).
    Rectangle {
        x: arc.sunX - width / 2
        y: arc.sunY - height / 2
        width: 12
        height: 12
        radius: 6
        visible: arc.daytime
        color: Qt.rgba(arc.colGlow.r, arc.colGlow.g, arc.colGlow.b, 0.35)
    }
    Rectangle {
        x: arc.sunX - width / 2
        y: arc.sunY - height / 2
        width: arc.ring ? 8 : 6
        height: width
        radius: width / 2
        visible: arc.known
        opacity: arc.daytime ? 1 : 0.45
        color: arc.ring ? "transparent" : arc.colSun
        border.width: arc.ring ? 1.6 : 0
        border.color: arc.colSun
    }
}
