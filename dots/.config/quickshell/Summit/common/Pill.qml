import QtQuick
import qs.common

// A group on a bar: a pane of frosted glass, its children in a row. It drops in when the shell starts (enterDelay
// staggers the groups) and settles with a little spring.
//
// The drop is `offset`, which the bar adds to the group's top margin: a real move of its geometry. A Translate would
// leave the bar's input region (its mask, made from the groups' geometry) where the group started, so the part of it
// that had moved would not take clicks.
Glass {
    id: root
    property int enterDelay: 0
    property real offset: -14
    opacity: 0
    Component.onCompleted: enter.start()
    SequentialAnimation {
        id: enter
        PauseAnimation { duration: root.enterDelay }
        ParallelAnimation {
            NumberAnimation { target: root; property: "opacity"; to: 1; duration: Theme.enterMs; easing.type: Easing.OutCubic }
            NumberAnimation { target: root; property: "offset"; to: 0; duration: Theme.enterMs; easing.type: Easing.OutBack; easing.overshoot: 1.6 }
        }
    }
    default property alias content: row.data
    property int padding: 6
    property alias spacing: row.spacing
    implicitWidth: row.implicitWidth + padding * 2
    implicitHeight: Theme.barHeight
    radius: Theme.radius

    // A click on the group itself, between its buttons (the right group's opens the side menu).
    property bool clickable: false
    signal clicked
    MouseArea {
        anchors.fill: parent
        enabled: root.clickable
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }

    Row {
        id: row
        anchors.verticalCenter: parent.verticalCenter
        x: root.padding
        spacing: 2
    }
}
