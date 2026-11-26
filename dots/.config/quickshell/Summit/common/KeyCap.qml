import QtQuick
import qs.common

// A key, drawn as a keycap: a raised face on a darker base. Super, Ctrl, Shift, Alt, Fn and Hyper have Summit's own
// icons (KeyIcon.qml) beside their names; any other key is its label (code font). Used by the cheat sheet and by
// hypr mode's card.
Item {
    id: root
    property string kind: ""
    property string label: ""
    property real size: 30
    readonly property bool modifier: root.kind !== ""

    implicitHeight: size
    implicitWidth: Math.max(size, content.implicitWidth + size * 0.55)

    // The base, a little lower: the key's side.
    Rectangle {
        anchors.fill: parent
        anchors.topMargin: 3
        radius: root.size * 0.26
        color: Theme.alpha(Theme.text, root.modifier ? 0.10 : 0.07)
    }
    // The face.
    Rectangle {
        id: face
        width: parent.width
        height: parent.height - 3
        radius: root.size * 0.26
        color: root.modifier ? Theme.alpha(Theme.accent, 0.20) : Theme.alpha(Theme.text, 0.12)
        border.width: 1
        border.color: root.modifier ? Theme.alpha(Theme.accent, 0.45) : Theme.alpha(Theme.text, 0.16)

        Row {
            id: content
            anchors.centerIn: parent
            spacing: root.size * 0.18
            KeyIcon {
                visible: root.modifier
                kind: root.kind
                size: root.size * 0.52
                stroke: root.size > 26 ? 2 : 1.6
                color: Theme.accent
                anchors.verticalCenter: parent.verticalCenter
            }
            Text {
                text: root.label
                color: Theme.text
                font.family: root.modifier ? Theme.font : Theme.mono
                font.pixelSize: root.size * (root.modifier ? 0.42 : 0.46)
                font.weight: Font.DemiBold
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }
}
