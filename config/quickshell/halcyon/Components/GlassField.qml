import QtQuick
import qs.Config

/** A single-line text field. */
FocusScope {
    id: root

    property string placeholder: ""
    property alias text: input.text
    property alias echoMode: input.echoMode
    property string glyph: ""
    property int radius: Theme.radiusMd

    signal accepted(string text)
    signal escaped

    implicitHeight: 40
    implicitWidth: 260

    Rectangle {
        anchors.fill: parent
        radius: root.radius
        color: Theme.surfaceSunken
        border.width: 1
        border.color: input.activeFocus ? Theme.accent : Theme.glassBorder

        Behavior on border.color {
            enabled: Theme.animationsEnabled
            ColorAnimation { duration: Theme.durInstant }
        }
    }

    Icon {
        id: leading
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.leftMargin: Theme.spacingMd
        visible: root.glyph.length > 0
        glyph: root.glyph
        size: Theme.sizeBodyLarge
        color: Theme.textTertiary
    }

    TextInput {
        id: input
        anchors.fill: parent
        anchors.leftMargin: leading.visible
            ? Theme.spacingMd * 2 + leading.width
            : Theme.spacingMd
        anchors.rightMargin: Theme.spacingMd
        verticalAlignment: TextInput.AlignVCenter

        focus: true
        color: Theme.text
        selectionColor: Theme.accent
        selectedTextColor: Theme.onAccent
        font.family: Theme.fontFamily
        font.pixelSize: Theme.sizeBody
        clip: true

        onAccepted: root.accepted(text)
        Keys.onEscapePressed: root.escaped()
    }

    Label {
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: input.left
        visible: input.text.length === 0
        text: root.placeholder
        tone: "tertiary"
    }

    Accessible.role: Accessible.EditableText
    Accessible.name: root.placeholder
}
