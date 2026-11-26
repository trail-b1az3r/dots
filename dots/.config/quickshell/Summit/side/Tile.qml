import QtQuick
import qs.common

// A quick toggle in the side menu, the Halcyon shell's quick panel's in a compact grid: an icon over a short name
// (the network, the device, what is on), filled in the accent while it is on. Click to toggle. One with a page of its
// own (Wi-Fi, Bluetooth, sound) has a small arrow in its corner that opens it (so does a right click).
Rectangle {
    id: root
    property string icon
    property string title
    property bool on: false
    property bool hasPage: false
    signal clicked
    signal pageRequested

    implicitHeight: 66
    radius: 18
    color: root.on ? Theme.accent : (area.containsMouse ? Theme.alpha(Theme.text, 0.13) : Theme.alpha(Theme.text, 0.08))
    Behavior on color { ColorAnimation { duration: Theme.animMs } }
    scale: area.pressed ? 0.94 : 1
    Behavior on scale { SpringAnimation { spring: Theme.springStiffness * 1.6; damping: Theme.springDamping; epsilon: 0.002 } }

    Symbol {
        anchors.horizontalCenter: parent.horizontalCenter
        y: 11
        name: root.icon
        size: 22
        fill: root.on ? 1 : 0
        color: root.on ? Theme.accentText : Theme.text
        Behavior on fill { NumberAnimation { duration: Theme.animMs } }
    }
    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        y: 40
        width: parent.width - 10
        horizontalAlignment: Text.AlignHCenter
        text: root.title
        color: root.on ? Theme.accentText : Theme.text
        font.family: Theme.font
        font.pixelSize: 11
        font.weight: Font.Medium
        elide: Text.ElideRight
    }
    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        cursorShape: Qt.PointingHandCursor
        onClicked: mouse => {
            if (mouse.button === Qt.RightButton && root.hasPage)
                root.pageRequested();
            else
                root.clicked();
        }
    }
    // The page's arrow: its own button, in the corner.
    Rectangle {
        visible: root.hasPage
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 3
        width: 22
        height: 22
        radius: 11
        color: arrowArea.containsMouse ? (root.on ? Theme.alpha(Theme.accentText, 0.18) : Theme.alpha(Theme.text, 0.14)) : "transparent"
        Symbol {
            anchors.centerIn: parent
            name: "chevron_right"
            size: 16
            color: root.on ? Theme.accentText : Theme.muted
        }
        MouseArea {
            id: arrowArea
            anchors.fill: parent
            anchors.margins: -4
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.pageRequested()
        }
    }
}
