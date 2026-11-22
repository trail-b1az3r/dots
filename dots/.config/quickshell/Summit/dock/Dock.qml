pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Wayland
import Quickshell.Widgets
import qs.common
import qs.services

// The bottom bar: a centred strip of apps on frosted glass. Pinned apps first, then whatever else is open; a dot
// under the running ones, a longer one under the focused. Click to focus or open. The window is taller than the
// strip so the app's name can show above it (only the strip takes the pointer: the mask).
PanelWindow {
    id: dock
    required property var modelData
    screen: modelData
    WlrLayershell.namespace: "summit-bottom"
    color: "transparent"
    anchors { bottom: true; left: true; right: true }
    implicitHeight: 64 + Theme.gap + 44
    exclusiveZone: 64 + Theme.gap
    mask: Region { item: strip }

    readonly property var pinned: Theme.data.pinned ?? ["firefox", "org.kde.dolphin", "kitty", "org.kde.kate", "code"]
    readonly property var toplevels: ToplevelManager.toplevels.values
    function running(appId) {
        return dock.toplevels.filter(t => (t.appId ?? "").toLowerCase() === appId.toLowerCase());
    }
    // Pinned ids, then the app ids of open windows not pinned (once each).
    readonly property var apps: {
        const ids = [...dock.pinned];
        for (const t of dock.toplevels) {
            const id = t.appId ?? "";
            if (id && !ids.some(p => p.toLowerCase() === id.toLowerCase()))
                ids.push(id);
        }
        return ids;
    }

    Glass {
        id: strip
        anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.bottom; bottomMargin: Theme.gap }
        height: 54
        width: row.implicitWidth + 16
        radius: Theme.radius + 4
        Behavior on width { NumberAnimation { duration: Theme.animMs; easing.type: Easing.OutCubic } }

        Row {
            id: row
            anchors.centerIn: parent
            spacing: 4

            BarButton {
                icon: "apps"
                implicitWidth: 42; implicitHeight: 42
                tint: Theme.accent
                onClicked: Actions.launcher()
            }
            Rectangle { width: 1; height: 26; color: Theme.alpha(Theme.text, 0.12); anchors.verticalCenter: parent.verticalCenter }

            Repeater {
                model: dock.apps
                delegate: Item {
                    id: app
                    required property string modelData
                    readonly property var entry: DesktopEntries.heuristicLookup(modelData)
                    readonly property var windows: dock.running(modelData)
                    readonly property bool focused: windows.some(t => t.activated)
                    width: 42; height: 42

                    Rectangle {
                        anchors.fill: parent
                        radius: Theme.radius - 2
                        color: area.containsMouse ? Theme.alpha(Theme.text, 0.08) : "transparent"
                        Behavior on color { ColorAnimation { duration: Theme.animMs } }
                    }
                    IconImage {
                        anchors.centerIn: parent
                        implicitSize: area.pressed ? 26 : 30
                        source: Quickshell.iconPath(app.entry?.icon ?? app.modelData, "application-x-executable")
                        Behavior on implicitSize { NumberAnimation { duration: 90 } }
                    }
                    Rectangle {
                        visible: app.windows.length > 0
                        anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.bottom; bottomMargin: -3 }
                        width: app.focused ? 14 : 4
                        height: 4
                        radius: 2
                        color: app.focused ? Theme.accent : Theme.alpha(Theme.text, 0.6)
                        Behavior on width { NumberAnimation { duration: Theme.animMs } }
                    }
                    MouseArea {
                        id: area
                        anchors.fill: parent
                        hoverEnabled: true
                        acceptedButtons: Qt.LeftButton | Qt.MiddleButton
                        cursorShape: Qt.PointingHandCursor
                        onClicked: mouse => {
                            if (mouse.button === Qt.LeftButton && app.windows.length > 0) {
                                // Cycle through its windows: the next after the focused one.
                                const i = app.windows.findIndex(t => t.activated);
                                app.windows[(i + 1) % app.windows.length].activate();
                            } else if (app.entry) {
                                app.entry.execute();
                            }
                        }
                    }
                    ToolTipLabel { target: area; text: app.entry?.name ?? app.modelData }
                }
            }
        }
    }
}
