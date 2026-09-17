import QtQuick
import qs.Config

/**
 * An indeterminate progress indicator.
 *
 * A dot orbiting a faint ring, rather than a rotating arc: drawing an arc
 * without Qt Quick Shapes means either a Canvas (CPU-rendered every
 * frame) or a shader (a build step), and neither is worth it for a 20px
 * indicator.
 *
 * With reduced motion on, the dot stops and pulses instead — a spinner is
 * the first animation people with vestibular sensitivity ask to lose, but
 * removing every sign of progress is worse than replacing it.
 */
Item {
    id: root

    property int size: 20
    property color color: Theme.accent
    property bool running: true

    implicitWidth: root.size
    implicitHeight: root.size

    Rectangle {
        id: track
        anchors.fill: parent
        radius: width / 2
        color: "transparent"
        border.width: Math.max(2, root.size / 9)
        border.color: Qt.rgba(root.color.r, root.color.g, root.color.b, 0.2)
    }

    Item {
        id: orbit
        anchors.fill: parent
        visible: !Theme.reducedMotion

        Rectangle {
            width: track.border.width * 1.9
            height: width
            radius: width / 2
            color: root.color
            x: (parent.width - width) / 2
            y: -height / 2 + track.border.width / 2
        }

        RotationAnimation on rotation {
            running: root.running && !Theme.reducedMotion && Theme.animationsEnabled
            loops: Animation.Infinite
            from: 0
            to: 360
            duration: 950
        }
    }

    Rectangle {
        anchors.centerIn: parent
        visible: Theme.reducedMotion
        width: root.size * 0.34
        height: width
        radius: width / 2
        color: root.color

        SequentialAnimation on opacity {
            running: root.running && Theme.reducedMotion
            loops: Animation.Infinite
            NumberAnimation { to: 0.3; duration: 700 }
            NumberAnimation { to: 1.0; duration: 700 }
        }
    }
}
