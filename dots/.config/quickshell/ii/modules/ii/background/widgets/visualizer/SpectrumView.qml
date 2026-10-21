pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Shapes
import qs.modules.common
import qs.modules.common.functions

/**
 * Draws a spectrum (AudioSpectrum.points, 0 to 1 per bar) in one of four styles, in two colours of the theme.
 *
 *   bars     rounded bars standing on the bottom edge
 *   mirror   the same bars grown from the middle line, up and down
 *   wave     a filled, smooth curve
 *   ring     bars round a circle, growing outward
 *
 * The bars themselves are drawn the theme's way (barStyle, from ThemeLook): round, pill, needle (a thin line with a
 * lit tip, Red Sun), shard (sharp, with a bright edge, glass), star (topped with a diamond, Star Rail) or blocks
 * (stacked keys, like a console's equaliser, the anime themes).
 *
 * Made of plain items and one Shape, so the scene graph draws it on the GPU: no canvas repainting every frame.
 */
Item {
    id: root

    /** One value per bar, 0 to 1. */
    property var points: []
    property string style: "bars"
    property string barStyle: "round"
    property color glowColor: colorA
    property int barCount: 48
    property color colorA: Appearance.colors.colPrimary
    property color colorB: Appearance.colors.colTertiary
    /** Bars resting at the least height, so the widget doesn't vanish between songs. */
    property real restingHeight: 3
    /** Fades the whole thing while nothing plays. */
    property bool live: true

    readonly property real gap: Math.max(1, Math.min(4, width / Math.max(barCount, 1) * 0.28))
    readonly property real barWidth: Math.max(1, (width - gap * (barCount - 1)) / Math.max(barCount, 1))

    opacity: live ? 1 : 0.4
    Behavior on opacity {
        NumberAnimation { duration: 600 }
    }

    function value(index: int): real {
        return root.points[index] ?? 0;
    }

    function blend(index: int): color {
        // ColorUtils.mix weights its first colour by the ratio, so B first: 0 is all A, 1 is all B.
        return ColorUtils.mix(root.colorB, root.colorA, barCount > 1 ? index / (barCount - 1) : 0);
    }

    // Bars and mirror
    Repeater {
        model: (root.style === "bars" || root.style === "mirror") ? root.barCount : 0

        delegate: Item {
            id: slot
            required property int index
            readonly property real fill: Math.max(root.restingHeight, root.value(index) * root.height)
            readonly property color tint: root.blend(index)
            readonly property bool mirror: root.style === "mirror"
            x: index * (root.barWidth + root.gap)
            width: root.barWidth
            height: mirror ? Math.min(root.height, fill) : fill
            y: mirror ? (root.height - height) / 2 : root.height - height

            // round, pill, shard and star: one bar
            Rectangle {
                visible: root.barStyle !== "needle" && root.barStyle !== "blocks"
                anchors.fill: parent
                radius: root.barStyle === "pill" ? width / 2 : (root.barStyle === "shard" ? 0 : (root.barStyle === "star" ? 1 : Math.min(width / 2, 6)))
                color: slot.tint
                // shard: a bright cut along the top
                Rectangle {
                    visible: root.barStyle === "shard"
                    width: parent.width
                    height: Math.min(2, parent.height)
                    color: Qt.rgba(1, 1, 1, 0.75)
                }
            }
            // star: a diamond riding on the bar
            Rectangle {
                visible: root.barStyle === "star" && slot.fill > root.restingHeight + 2
                width: Math.max(4, Math.min(9, root.barWidth))
                height: width
                rotation: 45
                x: (parent.width - width) / 2
                y: -width - 2
                color: Qt.lighter(slot.tint, 1.3)
            }

            // needle: a thin line with a lit tip
            Rectangle {
                visible: root.barStyle === "needle"
                width: Math.max(1.5, Math.min(root.barWidth * 0.35, 3))
                height: parent.height
                x: (parent.width - width) / 2
                color: Qt.rgba(slot.tint.r, slot.tint.g, slot.tint.b, 0.75)
            }
            Rectangle {
                visible: root.barStyle === "needle"
                width: Math.max(4, Math.min(root.barWidth, 7))
                height: width
                radius: width / 2
                x: (parent.width - width) / 2
                y: -width / 2
                color: root.glowColor
                Rectangle {
                    anchors.centerIn: parent
                    width: parent.width * 2.4
                    height: width
                    radius: width / 2
                    color: Qt.rgba(root.glowColor.r, root.glowColor.g, root.glowColor.b, 0.22)
                }
            }

            // blocks: stacked keys, lit from the bottom (from the middle out for the mirror). The cells are made once
            // for the full height and shown as the level rises, so nothing is created or destroyed per frame.
            Column {
                id: keys
                visible: root.barStyle === "blocks"
                anchors.bottom: parent.bottom
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 2
                readonly property real cell: Math.max(3, Math.min(root.barWidth, 9))
                readonly property int lit: Math.max(1, Math.floor((slot.height + spacing) / (cell + spacing)))
                Repeater {
                    model: root.barStyle === "blocks" ? Math.max(1, Math.floor((root.height + 2) / (Math.max(3, Math.min(root.barWidth, 9)) + 2))) : 0
                    delegate: Rectangle {
                        required property int index
                        visible: index < keys.lit
                        width: root.barWidth
                        height: keys.cell
                        radius: 2
                        color: slot.tint
                        border.width: root.barWidth > 6 ? 1 : 0
                        border.color: Qt.darker(slot.tint, 1.8)
                    }
                }
            }
        }
    }

    // Ring
    Repeater {
        model: root.style === "ring" ? root.barCount : 0

        delegate: Item {
            id: spoke
            required property int index
            readonly property real inner: Math.min(root.width, root.height) * 0.24
            readonly property real reach: Math.max(root.restingHeight, Math.min(root.width, root.height) * 0.5 - inner - 2)
            readonly property real length: Math.max(root.restingHeight, root.value(index) * reach)
            readonly property real thickness: Math.max(2, Math.min(7, 2 * Math.PI * inner / Math.max(root.barCount, 1) * 0.62))
            x: root.width / 2
            y: root.height / 2
            width: 0
            height: 0
            rotation: index * 360 / Math.max(root.barCount, 1)

            Rectangle {
                x: -spoke.thickness / 2
                y: -(spoke.inner + spoke.length)
                width: spoke.thickness
                height: spoke.length
                radius: width / 2
                color: root.blend(spoke.index)
            }
        }
    }

    // Wave
    Shape {
        id: waveShape
        anchors.fill: parent
        visible: root.style === "wave"
        preferredRendererType: Shape.CurveRenderer
        layer.enabled: visible
        layer.samples: 4

        // The curve passes through the middle of every bar's slot; the fill closes along the bottom edge.
        readonly property var curve: {
            const n = root.barCount;
            const out = [];
            for (let i = 0; i < n; i++)
                out.push(Qt.point(n > 1 ? i * root.width / (n - 1) : 0, root.height - Math.max(root.restingHeight, root.value(i) * root.height)));
            return out;
        }

        // The fill, closed along the bottom edge, with no outline of its own.
        ShapePath {
            strokeWidth: -1
            fillGradient: LinearGradient {
                x1: 0
                y1: 0
                x2: 0
                y2: waveShape.height
                GradientStop { position: 0; color: Qt.rgba(root.colorA.r, root.colorA.g, root.colorA.b, 0.7) }
                GradientStop { position: 1; color: Qt.rgba(root.colorB.r, root.colorB.g, root.colorB.b, 0.1) }
            }
            startX: 0
            startY: waveShape.height
            PathLine { x: 0; y: waveShape.curve.length > 0 ? waveShape.curve[0].y : waveShape.height }
            PathPolyline { path: waveShape.curve }
            PathLine { x: waveShape.width; y: waveShape.height }
            PathLine { x: 0; y: waveShape.height }
        }

        // The line along the top of it, and only that.
        ShapePath {
            strokeWidth: 2
            strokeColor: root.colorA
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            startX: waveShape.curve.length > 0 ? waveShape.curve[0].x : 0
            startY: waveShape.curve.length > 0 ? waveShape.curve[0].y : waveShape.height
            PathPolyline { path: waveShape.curve }
        }
    }
}
