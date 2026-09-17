import QtQuick
import qs.Config

/**
 * A slider.
 *
 * Dragging updates `value` continuously but only emits `committed` when
 * the pointer is released: a volume slider that sends fifty D-Bus calls
 * per drag is how a desktop earns a reputation for stuttering.
 */
Item {
    id: root

    property real value: 0.5
    property real from: 0.0
    property real to: 1.0
    property real step: 0.01
    property bool enabled: true
    property string glyph: ""
    property color fillColor: Theme.accent
    /** Shows the value as a percentage inside the track. */
    property bool showValue: false

    signal moved(real value)
    signal committed(real value)

    implicitHeight: 30
    implicitWidth: 180
    opacity: root.enabled ? 1.0 : 0.4

    readonly property real fraction: {
        const span = root.to - root.from;
        return span > 0 ? Math.max(0, Math.min(1, (root.value - root.from) / span)) : 0;
    }

    Rectangle {
        id: track
        anchors.fill: parent
        radius: height / 2
        color: Theme.surfaceSunken
        border.width: 1
        border.color: Theme.glassBorder
        clip: true

        Rectangle {
            id: fill
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: Math.max(parent.height, parent.width * root.fraction)
            radius: parent.radius
            color: root.fillColor

            Behavior on width {
                enabled: Theme.animationsEnabled && !pointer.pressed
                NumberAnimation {
                    duration: Theme.durQuick
                    easing.type: Easing.BezierSpline
                    easing.bezierCurve: Theme.easeDecel
                }
            }
        }

        Icon {
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: parent.left
            anchors.leftMargin: Theme.spacingSm
            visible: root.glyph.length > 0
            glyph: root.glyph
            size: Theme.sizeBody
            // The glyph sits over the fill, so it has to read against both.
            color: root.fraction > 0.14 ? Theme.onAccent : Theme.textSecondary
        }

        Label {
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: parent.right
            anchors.rightMargin: Theme.spacingMd
            visible: root.showValue
            text: Math.round(root.fraction * 100) + "%"
            variant: "caption"
            color: Theme.textSecondary
        }
    }

    MouseArea {
        id: pointer
        anchors.fill: parent
        enabled: root.enabled
        hoverEnabled: true
        cursorShape: root.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor

        function positionToValue(x: real): real {
            const fraction = Math.max(0, Math.min(1, x / root.width));
            const raw = root.from + fraction * (root.to - root.from);
            return root.step > 0 ? Math.round(raw / root.step) * root.step : raw;
        }

        onPressed: event => {
            root.value = positionToValue(event.x);
            root.moved(root.value);
        }
        onPositionChanged: event => {
            if (!pressed)
                return;
            root.value = positionToValue(event.x);
            root.moved(root.value);
        }
        onReleased: root.committed(root.value)

        onWheel: event => {
            const direction = event.angleDelta.y > 0 ? 1 : -1;
            const stride = Math.max(root.step, (root.to - root.from) / 20);
            root.value = Math.max(root.from, Math.min(root.to, root.value + direction * stride));
            root.moved(root.value);
            root.committed(root.value);
            event.accepted = true;
        }
    }

    Accessible.role: Accessible.Slider
    Accessible.value: root.value
    Accessible.minimumValue: root.from
    Accessible.maximumValue: root.to
}
