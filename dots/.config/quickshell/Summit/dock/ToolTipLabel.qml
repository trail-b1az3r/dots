import QtQuick
import qs.common

// A small name above a dock icon while the pointer is on it, on frosted glass.
Glass {
    id: root
    required property var target
    property string text
    // Fades in and rises a little; fades out.
    visible: opacity > 0
    opacity: target.containsMouse ? 1 : 0
    Behavior on opacity { NumberAnimation { duration: Theme.animMs; easing.type: Easing.OutCubic } }
    transform: Translate { y: root.target.containsMouse ? 0 : 6
        Behavior on y { NumberAnimation { duration: Theme.animMs; easing.type: Easing.OutCubic } } }
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
