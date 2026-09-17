import QtQuick
import qs.Config

/**
 * One row of a list: leading icon, title, subtitle, trailing slot.
 *
 * Used by Spotlight, the notification centre, Control Center's expanded
 * lists and Settings, which is why they line up with each other.
 */
Item {
    id: root

    property string title: ""
    property string subtitle: ""
    property string glyph: ""
    property string icon: ""
    property bool selected: false
    property bool enabled: true
    property int iconSize: 26

    default property alias trailing: trailingSlot.data

    signal activated
    signal rightClicked

    implicitHeight: root.subtitle.length > 0 ? 52 : 40
    implicitWidth: 320

    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusSm
        color: root.selected ? Theme.surfaceSelected : "transparent"

        Behavior on color {
            enabled: Theme.animationsEnabled
            ColorAnimation { duration: Theme.durInstant }
        }
    }

    Icon {
        id: leading
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.leftMargin: Theme.spacingMd
        visible: root.icon.length > 0 || root.glyph.length > 0
        source: root.icon
        glyph: root.glyph
        size: root.iconSize
        color: root.selected ? Theme.accentText : Theme.textSecondary
    }

    Column {
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: leading.visible ? leading.right : parent.left
        anchors.leftMargin: Theme.spacingMd
        anchors.right: trailingSlot.left
        anchors.rightMargin: Theme.spacingSm
        spacing: 1

        Label {
            width: parent.width
            text: root.title
            variant: "body"
            font.weight: root.selected ? Theme.weightMedium : Theme.weightRegular
        }

        Label {
            width: parent.width
            visible: root.subtitle.length > 0
            text: root.subtitle
            variant: "footnote"
            tone: "tertiary"
        }
    }

    Item {
        id: trailingSlot
        anchors.verticalCenter: parent.verticalCenter
        anchors.right: parent.right
        anchors.rightMargin: Theme.spacingMd
        width: childrenRect.width
        height: parent.height
    }

    StateLayer {
        anchors.fill: parent
        radius: Theme.radiusSm
        enabled: root.enabled
        onClicked: root.activated()
        onRightClicked: root.rightClicked()
    }

    Accessible.role: Accessible.ListItem
    Accessible.name: root.title
    Accessible.description: root.subtitle
}
