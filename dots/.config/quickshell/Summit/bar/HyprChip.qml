import QtQuick
import qs.common
import qs.services

// Hypr mode on the bar: a chip in the accent that grows out of the left group while the mode is on, and folds away
// when it ends. Its width is a real size (the group around it grows with it), so the bar's input region follows.
Item {
    id: root
    readonly property bool on: HyprModeState.active
    implicitHeight: Theme.barHeight - 10
    implicitWidth: on ? chip.implicitWidth + 4 : 0
    clip: true
    Behavior on implicitWidth { SpringAnimation { spring: Theme.springStiffness; damping: Theme.springDamping + 0.08; epsilon: 0.3 } }

    Rectangle {
        id: chip
        anchors.verticalCenter: parent.verticalCenter
        x: 4
        implicitWidth: row.implicitWidth + 18
        height: parent.height - 4
        radius: height / 2
        color: Theme.accent
        opacity: root.on ? 1 : 0
        scale: root.on ? 1 : 0.6
        Behavior on opacity { NumberAnimation { duration: Theme.animMs } }
        Behavior on scale { NumberAnimation { duration: Theme.enterMs; easing.type: Easing.OutBack; easing.overshoot: 2 } }

        Row {
            id: row
            anchors.centerIn: parent
            spacing: 5
            Symbol {
                name: "keyboard"
                size: 16
                fill: 1
                color: Theme.accentText
                anchors.verticalCenter: parent.verticalCenter
            }
            Text {
                text: "HYPR"
                color: Theme.accentText
                font.family: Theme.font
                font.pixelSize: 11
                font.weight: Font.Bold
                font.letterSpacing: 1.2
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }
}
