import QtQuick
import qs.Config

/**
 * A switch.
 *
 * The knob overshoots very slightly on the way in and settles — the one
 * place in the design system where a spring is worth the frames, because
 * a toggle is the control people watch while they use it.
 */
Item {
    id: root

    property bool checked: false
    property bool enabled: true
    signal toggled(bool value)

    implicitWidth: 44
    implicitHeight: 26
    opacity: root.enabled ? 1.0 : 0.4

    Rectangle {
        id: track
        anchors.fill: parent
        radius: height / 2
        color: root.checked ? Theme.accent : Theme.surfaceSunken
        border.width: root.checked ? 0 : 1
        border.color: Theme.glassBorder

        Behavior on color {
            enabled: Theme.animationsEnabled
            ColorAnimation {
                duration: Theme.durQuick
                easing.type: Easing.BezierSpline
                easing.bezierCurve: Theme.easeStandard
            }
        }
    }

    Rectangle {
        id: knob
        y: 3
        width: 20
        height: 20
        radius: height / 2
        x: root.checked ? root.width - width - 3 : 3
        color: root.checked ? Theme.onAccent : Theme.textSecondary

        Behavior on x {
            enabled: Theme.animationsEnabled
            NumberAnimation {
                duration: Theme.durQuick
                easing.type: Easing.BezierSpline
                easing.bezierCurve: Theme.reducedMotion ? Theme.easeStandard : Theme.easeOvershoot
            }
        }
        Behavior on color {
            enabled: Theme.animationsEnabled
            ColorAnimation { duration: Theme.durQuick }
        }
    }

    StateLayer {
        anchors.fill: parent
        radius: height / 2
        enabled: root.enabled
        focusVisible: root.activeFocus
        onClicked: {
            root.checked = !root.checked;
            root.toggled(root.checked);
        }
    }

    Accessible.role: Accessible.CheckBox
    Accessible.checked: root.checked
    Accessible.onToggleAction: {
        root.checked = !root.checked;
        root.toggled(root.checked);
    }
}
