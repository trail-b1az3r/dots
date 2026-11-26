pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Services.Notifications
import qs.common

// One notification: the app's icon (or the picture it sent), the app and when, the title, the body (two lines;
// all of it when `expanded`), and its buttons. Clicking it does the notification's default action, if it has one;
// the cross dismisses it. Used by the popups and the side menu.
Rectangle {
    id: root
    required property var notification
    property bool expanded: false
    property bool showClose: true
    property date arrived: new Date()
    signal closed

    readonly property bool critical: notification?.urgency === NotificationUrgency.Critical
    readonly property var actions: (notification?.actions ?? []).filter(a => a.identifier !== "default")
    readonly property var defaultAction: (notification?.actions ?? []).find(a => a.identifier === "default") ?? null

    implicitHeight: col.implicitHeight + 24
    radius: Theme.radius
    color: area.containsMouse ? Theme.alpha(Theme.text, 0.10) : Theme.alpha(Theme.text, 0.06)
    border.width: root.critical ? 1 : 0
    border.color: Theme.alpha("#FF8A80", 0.7)
    Behavior on color { ColorAnimation { duration: Theme.animMs } }

    function ago(date) {
        const s = Math.max(0, (Date.now() - date.getTime()) / 1000);
        return s < 60 ? "now" : s < 3600 ? Math.floor(s / 60) + " min" : s < 86400 ? Math.floor(s / 3600) + " h"
            : Qt.formatDate(date, "d MMM");
    }

    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: root.defaultAction ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: {
            if (root.defaultAction) {
                root.defaultAction.invoke();
                root.closed();
            } else {
                root.expanded = !root.expanded;
            }
        }
    }

    Row {
        id: top
        x: 12
        y: 12
        width: parent.width - 24
        spacing: 10

        // The picture it sent, else the app's icon, else a bell.
        Item {
            width: 36
            height: 36
            Image {
                id: picture
                anchors.fill: parent
                source: root.notification?.image ?? ""
                fillMode: Image.PreserveAspectCrop
                visible: status === Image.Ready
                sourceSize: Qt.size(72, 72)
                asynchronous: true
            }
            Image {
                id: appIcon
                anchors.fill: parent
                anchors.margins: 2
                visible: !picture.visible && status === Image.Ready
                source: {
                    const icon = root.notification?.appIcon ?? "";
                    return icon === "" ? "" : icon.startsWith("/") || icon.includes("://") ? icon : Quickshell.iconPath(icon, true);
                }
                sourceSize: Qt.size(64, 64)
                asynchronous: true
            }
            Rectangle {
                anchors.fill: parent
                radius: 10
                visible: !picture.visible && !appIcon.visible
                color: Theme.alpha(Theme.accent, 0.18)
                Symbol {
                    anchors.centerIn: parent
                    name: "notifications"
                    fill: 1
                    color: Theme.accent
                }
            }
        }

        Column {
            id: col
            width: parent.width - 46 - (root.showClose ? 28 : 0)
            spacing: 3
            Row {
                width: parent.width
                spacing: 6
                Text {
                    text: root.notification?.appName || "Notification"
                    color: Theme.muted
                    font.family: Theme.font
                    font.pixelSize: 11
                    font.weight: Font.Medium
                    elide: Text.ElideRight
                    width: Math.min(implicitWidth, parent.width - when.implicitWidth - 6)
                }
                Text {
                    id: when
                    text: "· " + root.ago(root.arrived)
                    color: Theme.muted
                    font.family: Theme.font
                    font.pixelSize: 11
                }
            }
            Text {
                width: parent.width
                text: root.notification?.summary ?? ""
                visible: text !== ""
                color: Theme.text
                font.family: Theme.font
                font.pixelSize: 13
                font.weight: Font.DemiBold
                wrapMode: Text.Wrap
                maximumLineCount: root.expanded ? 4 : 1
                elide: Text.ElideRight
            }
            Text {
                width: parent.width
                text: root.notification?.body ?? ""
                visible: text !== ""
                color: Theme.alpha(Theme.text, 0.82)
                font.family: Theme.font
                font.pixelSize: 12
                textFormat: Text.StyledText
                wrapMode: Text.Wrap
                maximumLineCount: root.expanded ? 12 : 2
                elide: Text.ElideRight
                linkColor: Theme.accent
                onLinkActivated: link => Qt.openUrlExternally(link)
            }
            // Its buttons.
            Flow {
                width: parent.width
                spacing: 6
                topPadding: root.actions.length ? 6 : 0
                visible: root.actions.length > 0
                Repeater {
                    model: root.actions
                    delegate: Rectangle {
                        id: button
                        required property var modelData
                        width: label.implicitWidth + 22
                        height: 28
                        radius: 14
                        color: buttonArea.containsMouse ? Theme.alpha(Theme.accent, 0.32) : Theme.alpha(Theme.accent, 0.18)
                        Behavior on color { ColorAnimation { duration: Theme.animMs } }
                        Text {
                            id: label
                            anchors.centerIn: parent
                            text: button.modelData.text
                            color: Theme.text
                            font.family: Theme.font
                            font.pixelSize: 12
                            font.weight: Font.Medium
                        }
                        MouseArea {
                            id: buttonArea
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                button.modelData.invoke();
                                root.closed();
                            }
                        }
                    }
                }
            }
        }
    }

    BarButton {
        visible: root.showClose
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 6
        implicitHeight: 26
        icon: "close"
        opacity: area.containsMouse || hovered ? 1 : 0.45
        property bool hovered: false
        onClicked: {
            root.notification?.dismiss();
            root.closed();
        }
    }
}
