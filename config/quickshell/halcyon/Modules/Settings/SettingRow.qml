import QtQuick
import QtQuick.Layouts
import qs.Config
import qs.Components

/**
 * One setting: a label, an explanation, and a control.
 *
 * Every section is built from these, so the label column lines up down
 * the whole application and adding a setting is one element rather than
 * a layout exercise.
 */
RowLayout {
    id: root

    property string title: ""
    property string description: ""

    default property alias control: slot.data

    Layout.fillWidth: true
    spacing: Theme.spacingLg

    ColumnLayout {
        Layout.fillWidth: true
        spacing: 0

        Label {
            Layout.fillWidth: true
            text: root.title
            variant: "body"
        }

        Label {
            Layout.fillWidth: true
            visible: root.description.length > 0
            text: root.description
            variant: "caption"
            tone: "tertiary"
            wrapMode: Text.WordWrap
        }
    }

    Item {
        id: slot
        Layout.alignment: Qt.AlignVCenter
        Layout.preferredWidth: childrenRect.width
        Layout.preferredHeight: Math.max(28, childrenRect.height)
    }
}
