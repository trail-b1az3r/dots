pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Services.SystemTray
import Quickshell.Widgets
import qs.common

// Tray icons, monochrome-calm: click to open the app, right-click for its menu.
Row {
    id: root
    spacing: 2
    visible: SystemTray.items.values.length > 0

    Repeater {
        model: SystemTray.items
        delegate: Rectangle {
            id: slot
            required property SystemTrayItem modelData
            width: Theme.barHeight - 10
            height: width
            radius: Theme.radius - 4
            color: area.containsMouse ? Theme.alpha(Theme.text, 0.08) : "transparent"
            IconImage {
                anchors.centerIn: parent
                implicitSize: 16
                source: slot.modelData.icon
            }
            MouseArea {
                id: area
                anchors.fill: parent
                hoverEnabled: true
                acceptedButtons: Qt.LeftButton | Qt.RightButton
                onClicked: mouse => {
                    if (mouse.button === Qt.LeftButton && !slot.modelData.onlyMenu) {
                        slot.modelData.activate();
                    } else if (slot.modelData.hasMenu) {
                        const p = slot.mapToItem(null, 0, slot.height + 6);
                        slot.modelData.display(slot.QsWindow.window, p.x, p.y);
                    }
                }
            }
        }
    }
}
