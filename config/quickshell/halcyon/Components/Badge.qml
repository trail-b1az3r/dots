import QtQuick
import qs.Config

/** A small count or status pill. */
Rectangle {
    id: root

    property string text: ""
    property color background: Theme.accent
    property color foreground: Theme.onAccent

    implicitWidth: Math.max(label.implicitWidth + Theme.spacingSm * 2, implicitHeight)
    implicitHeight: 18
    radius: height / 2
    color: root.background

    Label {
        id: label
        anchors.centerIn: parent
        text: root.text
        variant: "caption"
        font.weight: Theme.weightSemibold
        color: root.foreground
    }
}
