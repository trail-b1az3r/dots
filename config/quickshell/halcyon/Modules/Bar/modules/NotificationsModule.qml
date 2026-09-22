import QtQuick
import qs.Config
import qs.Services
import qs.Components
import "../"

/** Unread count; opens the notification centre. */
BarItem {
    id: root

    property var hostBar: null

    readonly property bool dnd: Config.get("notifications.doNotDisturb", false)

    tooltip: {
        if (root.dnd) {
            return qsTr("Do Not Disturb is on");
        }
        return Notifications.unread > 0
            ? qsTr("%n unread notification(s)", "", Notifications.unread)
            : qsTr("No unread notifications");
    }

    onActivated: Actions.run(["shell", "notifications", "toggle"])
    onSecondaryActivated: Actions.run(["notify", "dnd", "toggle"])

    content: Row {
        spacing: Theme.spacingXs

        Icon {
            anchors.verticalCenter: parent.verticalCenter
            glyph: root.dnd ? "\udb81\udc9b" : "\udb80\udf9a"
            size: Theme.sizeBody
            color: root.dnd ? Theme.textTertiary
                : (Notifications.unread > 0 ? Theme.accent : Theme.textSecondary)
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            visible: Notifications.unread > 0 && !root.dnd
            text: Notifications.unread
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeCaption
            font.features: ({ "tnum": 1 })
            renderType: Text.QtRendering
        }
    }
}
