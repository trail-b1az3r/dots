import QtQuick
import qs.Config

/**
 * The dimming layer behind a modal surface.
 *
 * Clicking it dismisses — the behaviour people expect from every overlay
 * on every platform, and the reason it is a component rather than a
 * Rectangle copied into six places.
 */
Rectangle {
    id: root

    property bool shown: false
    signal dismissed

    anchors.fill: parent
    color: Theme.scrim
    opacity: root.shown ? 1 : 0
    visible: opacity > 0.01

    Behavior on opacity {
        enabled: Theme.animationsEnabled
        NumberAnimation {
            duration: Theme.durOverlay
            easing.type: Easing.BezierSpline
            easing.bezierCurve: Theme.easeStandard
        }
    }

    MouseArea {
        anchors.fill: parent
        enabled: root.shown
        onClicked: root.dismissed()
    }
}
