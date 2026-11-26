import QtQuick
import qs.common

// An on/off switch, as the battery popup's.
Rectangle {
    id: root
    property bool checked: false
    signal toggled
    implicitWidth: 44
    implicitHeight: 26
    radius: height / 2
    color: root.checked ? Theme.accent : Theme.alpha(Theme.text, 0.22)
    Behavior on color { ColorAnimation { duration: Theme.animMs } }
    Rectangle {
        width: 20
        height: 20
        radius: 10
        anchors.verticalCenter: parent.verticalCenter
        x: root.checked ? parent.width - width - 3 : 3
        color: root.checked ? Theme.accentText : Theme.text
        Behavior on x { NumberAnimation { duration: Theme.animMs; easing.type: Easing.OutBack } }
    }
    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: root.toggled()
    }
}
