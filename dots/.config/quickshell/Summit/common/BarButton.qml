import QtQuick
import qs.common

// A button on a bar: an icon, an optional label, a soft highlight under the pointer.
Rectangle {
    id: root
    property string icon
    property string label
    property bool active: false
    property color tint: Theme.text
    signal clicked
    signal rightClicked
    signal scrolled(int delta)

    implicitWidth: Math.max(implicitHeight, content.implicitWidth + 18)
    implicitHeight: Theme.barHeight - 10
    radius: Theme.radius - 4
    color: active ? Theme.alpha(Theme.accent, 0.22) : area.containsMouse ? Theme.alpha(Theme.text, 0.08) : "transparent"
    Behavior on color { ColorAnimation { duration: Theme.animMs } }

    Row {
        id: content
        anchors.centerIn: parent
        spacing: 6
        Symbol {
            visible: root.icon !== ""
            name: root.icon
            fill: root.active ? 1 : 0
            color: root.active ? Theme.accent : root.tint
            anchors.verticalCenter: parent.verticalCenter
        }
        Text {
            visible: root.label !== ""
            text: root.label
            color: root.tint
            font.family: Theme.font
            font.pixelSize: Theme.fontSize
            font.weight: Font.Medium
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        cursorShape: Qt.PointingHandCursor
        onClicked: mouse => mouse.button === Qt.RightButton ? root.rightClicked() : root.clicked()
        onWheel: wheel => root.scrolled(wheel.angleDelta.y)
    }
}
