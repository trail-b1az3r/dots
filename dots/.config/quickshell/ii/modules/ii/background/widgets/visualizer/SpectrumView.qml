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
 * Made of plain items and one Shape, so the scene graph draws it on the GPU: no canvas repainting every frame.
 */
Item {
    id: root

    /** One value per bar, 0 to 1. */
    property var points: []
    property string style: "bars"
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

        delegate: Rectangle {
            required property int index
            readonly property real fill: Math.max(root.restingHeight, root.value(index) * root.height)
            x: index * (root.barWidth + root.gap)
            width: root.barWidth
            height: root.style === "mirror" ? Math.min(root.height, fill) : fill
            y: root.style === "mirror" ? (root.height - height) / 2 : root.height - height
            radius: Math.min(width / 2, 6)
            color: root.blend(index)
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
