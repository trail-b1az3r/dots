import QtQuick
import qs.common

// A small name above a dock icon while the pointer is on it, on frosted glass.
Glass {
    id: root
    required property var target
    property string text
    visible: target.containsMouse
    anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.top; bottomMargin: 8 }
    width: label.implicitWidth + 20
    height: label.implicitHeight + 10
    radius: height / 2
    tint: Theme.glassTint + 0.25
    highlight: 0.06
    Text {
        id: label
        anchors.centerIn: parent
        text: root.text
        color: Theme.text
        font.family: Theme.font
        font.pixelSize: 12
    }
}
