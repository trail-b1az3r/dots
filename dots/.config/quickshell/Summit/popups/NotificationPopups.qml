pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Wayland
import Quickshell.Hyprland
import Quickshell.Services.Notifications
import qs.common
import qs.services

// New notifications, in the top right corner of the focused screen, under the bar: each slides in from the edge and
// goes after its time (the app's, or five seconds; never by itself if it is critical). The pointer on one keeps it.
// All of them stay in the side menu until dismissed. Important ones go to the banner under the clock instead.
Scope {
    id: root

    LazyLoader {
        active: Notifs.popups.length > 0

        PanelWindow {
            id: window
            screen: Quickshell.screens.find(s => s.name === Hyprland.focusedMonitor?.name) ?? Quickshell.screens[0]
            color: "transparent"
            WlrLayershell.namespace: "summit-notifications"
            WlrLayershell.layer: WlrLayer.Overlay
            anchors { top: true; right: true }
            margins { top: Theme.gap; right: Theme.gap }
            implicitWidth: 380
            implicitHeight: Math.max(1, stack.implicitHeight)
            exclusiveZone: 0
            mask: Region { item: stack }

            Column {
                id: stack
                width: parent.width
                spacing: 8
                Repeater {
                    model: Notifs.popups
                    delegate: Item {
                        id: popup
                        required property var modelData
                        readonly property var notification: modelData.notification
                        width: stack.width
                        height: card.implicitHeight
                        // In from the right edge.
                        property real slide: 1
                        Component.onCompleted: enter.start()
                        NumberAnimation { id: enter; target: popup; property: "slide"; from: 1; to: 0; duration: Theme.enterMs; easing.type: Easing.OutBack; easing.overshoot: 1.2 }
                        SequentialAnimation {
                            id: leave
                            NumberAnimation { target: popup; property: "slide"; to: 1.1; duration: 240; easing.type: Easing.InCubic }
                            ScriptAction { script: Notifs.closePopup(popup.modelData.id) }
                        }
                        function close() { if (!leave.running) leave.start(); }

                        Timer {
                            interval: (popup.notification?.expireTimeout ?? 0) > 0 ? popup.notification.expireTimeout : 5000
                            running: popup.notification?.urgency !== NotificationUrgency.Critical && !hover.hovered
                            onTriggered: popup.close()
                        }
                        Connections {
                            target: popup.notification
                            function onClosed() { popup.close(); }
                        }

                        Glass {
                            id: card
                            x: popup.slide * (stack.width + Theme.gap)
                            width: parent.width
                            implicitHeight: content.implicitHeight
                            radius: Theme.radius + 4
                            tint: Theme.glassTint + 0.2
                            HoverHandler { id: hover }
                            NotificationCard {
                                id: content
                                width: parent.width
                                notification: popup.notification
                                color: "transparent"
                                onClosed: popup.close()
                            }
                        }
                    }
                }
            }
        }
    }
}
