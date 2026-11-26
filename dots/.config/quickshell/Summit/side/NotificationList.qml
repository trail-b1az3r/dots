pragma ComponentBehavior: Bound

import QtQuick
import qs.common
import qs.services

// Every notification not yet dismissed, newest first, with clear-all; the bell says when do not disturb is on.
Rectangle {
    id: root
    radius: Theme.radius + 2
    color: Theme.alpha(Theme.text, 0.06)
    clip: true

    // When each arrived (the server does not say): noted the first time it is seen.
    property var seen: ({})
    function arrivedAt(n) {
        const key = n?.id ?? 0;
        if (!root.seen[key])
            root.seen[key] = new Date();
        return root.seen[key];
    }

    Item {
        id: head
        x: 14
        y: 10
        width: parent.width - 28
        height: 30
        Row {
            anchors.verticalCenter: parent.verticalCenter
            spacing: 8
            Text {
                text: "Notifications"
                color: Theme.text
                font.family: Theme.font
                font.pixelSize: 14
                font.weight: Font.DemiBold
                anchors.verticalCenter: parent.verticalCenter
            }
            Rectangle {
                visible: Notifs.count > 0
                width: Math.max(20, count.implicitWidth + 10)
                height: 20
                radius: 10
                color: Theme.alpha(Theme.accent, 0.25)
                anchors.verticalCenter: parent.verticalCenter
                Text {
                    id: count
                    anchors.centerIn: parent
                    text: Notifs.count
                    color: Theme.text
                    font.family: Theme.font
                    font.pixelSize: 11
                    font.weight: Font.DemiBold
                }
            }
            Symbol {
                visible: Prefs.doNotDisturb
                name: "do_not_disturb_on"
                size: 16
                color: Theme.muted
                anchors.verticalCenter: parent.verticalCenter
            }
        }
        BarButton {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            visible: Notifs.count > 0
            implicitHeight: 28
            icon: "clear_all"
            label: "Clear"
            onClicked: Notifs.clearAll()
        }
    }

    ListView {
        id: list
        anchors.top: head.bottom
        anchors.topMargin: 6
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 8
        x: 8
        width: parent.width - 16
        spacing: 6
        clip: true
        model: Notifs.newestFirst
        boundsBehavior: Flickable.StopAtBounds
        add: Transition {
            ParallelAnimation {
                NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.animMs }
                NumberAnimation { property: "x"; from: 40; to: 0; duration: Theme.enterMs; easing.type: Easing.OutCubic }
            }
        }
        displaced: Transition {
            NumberAnimation { properties: "y"; duration: Theme.animMs; easing.type: Easing.OutCubic }
        }
        delegate: NotificationCard {
            required property var modelData
            width: list.width
            notification: modelData
            arrived: root.arrivedAt(modelData)
        }
    }

    Column {
        anchors.centerIn: list
        visible: Notifs.count === 0
        spacing: 6
        opacity: 0.7
        Symbol {
            anchors.horizontalCenter: parent.horizontalCenter
            name: "notifications_off"
            size: 34
            color: Theme.muted
        }
        Text {
            text: "Nothing new"
            color: Theme.muted
            font.family: Theme.font
            font.pixelSize: 13
        }
    }
}
