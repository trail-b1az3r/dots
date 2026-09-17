import QtQuick
import qs.Config

/**
 * The hover / press / focus wash that sits over an interactive surface.
 *
 * Separated out because every control needs the same three states with
 * the same timings, and because putting the MouseArea here means each
 * control does not re-implement "did the pointer leave while pressed".
 */
Item {
    id: root

    property int radius: Theme.radiusSm
    property bool enabled: true
    property bool focusVisible: false
    property color hoverColor: Theme.surfaceHover
    property color pressColor: Theme.surfacePressed

    signal clicked
    signal rightClicked
    signal wheel(int delta)

    readonly property bool hovered: mouse.containsMouse && root.enabled
    readonly property bool pressed: mouse.pressed && root.enabled

    Rectangle {
        anchors.fill: parent
        radius: root.radius
        color: root.pressed ? root.pressColor : (root.hovered ? root.hoverColor : "transparent")

        Behavior on color {
            enabled: Theme.animationsEnabled
            ColorAnimation {
                duration: Theme.durInstant
                easing.type: Easing.BezierSpline
                easing.bezierCurve: Theme.easeStandard
            }
        }
    }

    // The keyboard focus ring. Drawn inside the bounds so it cannot be
    // clipped away by a parent, and only when focus arrived from the
    // keyboard — a ring around every clicked button is noise.
    Rectangle {
        anchors.fill: parent
        radius: root.radius
        color: "transparent"
        border.width: 2
        border.color: Theme.accent
        opacity: (root.focusVisible && Theme.focusRing) ? 1 : 0

        Behavior on opacity {
            enabled: Theme.animationsEnabled
            NumberAnimation { duration: Theme.durInstant }
        }
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        enabled: root.enabled
        hoverEnabled: true
        cursorShape: root.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        acceptedButtons: Qt.LeftButton | Qt.RightButton

        onClicked: event => {
            if (event.button === Qt.RightButton)
                root.rightClicked();
            else
                root.clicked();
        }

        onWheel: event => {
            root.wheel(event.angleDelta.y);
            event.accepted = true;
        }
    }
}
