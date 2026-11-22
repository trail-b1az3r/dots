import QtQuick
import qs.common

// A group on a bar: a pane of frosted glass, its children in a row. It drops in when the shell starts (enterDelay
// staggers the groups) and settles with a little spring.
Glass {
    id: root
    property int enterDelay: 0
    opacity: 0
    transform: Translate { id: drop; y: -14 }
    Component.onCompleted: enter.start()
    SequentialAnimation {
        id: enter
        PauseAnimation { duration: root.enterDelay }
        ParallelAnimation {
            NumberAnimation { target: root; property: "opacity"; to: 1; duration: Theme.enterMs; easing.type: Easing.OutCubic }
            NumberAnimation { target: drop; property: "y"; to: 0; duration: Theme.enterMs; easing.type: Easing.OutBack; easing.overshoot: 1.6 }
        }
    }
    default property alias content: row.data
    property int padding: 6
    property alias spacing: row.spacing
    implicitWidth: row.implicitWidth + padding * 2
    implicitHeight: Theme.barHeight
    radius: Theme.radius

    Row {
        id: row
        anchors.verticalCenter: parent.verticalCenter
        x: root.padding
        spacing: 2
    }
}
