import QtQuick
import qs.Config
import qs.Components

/**
 * The shape every bar module has: a pill that responds to the pointer.
 *
 * Modules differ in what they show, not in how they behave. Putting the
 * hover, press, scroll and click handling here means a module is a
 * label and an action, and the whole row feels like one control rather
 * than twenty-three separately-invented ones.
 *
 * Nothing here decides what a module does — that is the module's
 * `onActivated`. This only makes the interaction consistent.
 */
Item {
    id: root

    /** Shown in the bar's shared tooltip while the pointer is over it. */
    property string tooltip: ""
    property bool interactive: true
    /** Draws the accent-tinted background even when not hovered. */
    property bool active: false
    property int horizontalPadding: Theme.spacingSm
    property alias content: holder.data

    signal activated
    signal secondaryActivated
    signal middleActivated
    signal scrolledUp
    signal scrolledDown

    readonly property bool hovered: hover.hovered
    readonly property bool pressed: tap.pressed

    implicitWidth: holder.implicitWidth + root.horizontalPadding * 2
    implicitHeight: parent ? parent.height : Theme.spacingXl

    Rectangle {
        id: background

        anchors.fill: parent
        anchors.topMargin: Theme.spacingXs
        anchors.bottomMargin: Theme.spacingXs
        radius: Theme.radiusSm
        color: {
            if (!root.interactive) {
                return "transparent";
            }
            if (root.pressed) {
                return Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.28);
            }
            if (root.active) {
                return Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.18);
            }
            if (root.hovered) {
                return Qt.rgba(Theme.text.r, Theme.text.g, Theme.text.b, 0.10);
            }
            return "transparent";
        }

        Behavior on color {
            enabled: Theme.animationsEnabled
            ColorAnimation {
                duration: Theme.durQuick
                easing.type: Easing.Bezier
                easing.bezierCurve: Theme.curve("standard")
            }
        }
    }

    Item {
        id: holder

        anchors.centerIn: parent
        implicitWidth: childrenRect.width
        implicitHeight: childrenRect.height
    }

    HoverHandler {
        id: hover

        enabled: root.interactive
        cursorShape: Qt.PointingHandCursor
    }

    TapHandler {
        id: tap

        enabled: root.interactive
        acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
        onTapped: (eventPoint, button) => {
            if (button === Qt.RightButton) {
                root.secondaryActivated();
            } else if (button === Qt.MiddleButton) {
                root.middleActivated();
            } else {
                root.activated();
            }
        }
    }

    WheelHandler {
        enabled: root.interactive
        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
        onWheel: event => {
            // Touchpads deliver many small deltas; a threshold stops one
            // physical gesture from firing a dozen volume steps.
            if (event.angleDelta.y > 12) {
                root.scrolledUp();
            } else if (event.angleDelta.y < -12) {
                root.scrolledDown();
            }
        }
    }
}
