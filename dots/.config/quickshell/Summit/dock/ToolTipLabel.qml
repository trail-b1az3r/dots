import QtQuick
import qs.common

// A small name above a dock icon while the pointer is on it.
Rectangle {
    id: root
    required property var target
    property string text
    visible: target.containsMouse
    anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.top; bottomMargin: 8 }
    width: label.implicitWidth + 16
    height: 24
    radius: 8
    color: Theme.alpha(Theme.surfaceHigh, 0.96)
    Text {
        id: label
        anchors.centerIn: parent
        text: root.text
        color: Theme.text
        font.family: Theme.font
        font.pixelSize: 12
    }
}
