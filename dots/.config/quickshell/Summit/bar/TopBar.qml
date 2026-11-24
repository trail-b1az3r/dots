pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.common
import qs.services
import qs.popups

// The top bar: three floating groups on the wallpaper. Left, the launcher and the workspaces; centre, the date,
// time and weather; right, the tray, network, sound, battery and power.
PanelWindow {
    id: bar
    required property var modelData
    screen: modelData
    WlrLayershell.namespace: "summit-top"
    color: "transparent"
    anchors { top: true; left: true; right: true }
    implicitHeight: Theme.barHeight + Theme.gap
    exclusiveZone: Theme.barHeight + Theme.gap
    mask: Region {
        Region { item: left }
        Region { item: centre }
        Region { item: right }
    }

    Pill {
        id: left
        enterDelay: 0
        anchors { left: parent.left; leftMargin: Theme.gap; top: parent.top; topMargin: Theme.gap + left.offset }
        BarButton {
            icon: "landscape"
            tint: Theme.accent
            onClicked: Actions.launcher()
            onRightClicked: Actions.themes()
        }
        Workspaces {
            screen: bar.modelData
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    Pill {
        id: centre
        enterDelay: 70
        anchors { horizontalCenter: parent.horizontalCenter; top: parent.top; topMargin: Theme.gap + centre.offset }
        Clock {
            id: clock
            onToggled: calendar.visible = !calendar.visible
        }
        WeatherChip {}
    }

    Pill {
        id: right
        enterDelay: 140
        anchors { right: parent.right; rightMargin: Theme.gap; top: parent.top; topMargin: Theme.gap + right.offset }
        Tray { anchors.verticalCenter: parent.verticalCenter }
        Status {
            anchors.verticalCenter: parent.verticalCenter
            onBatteryClicked: batteryPopup.visible = !batteryPopup.visible
        }
    }

    Calendar {
        id: calendar
        anchor.window: bar
        anchor.rect.x: centre.x + centre.width / 2 - implicitWidth / 2
        anchor.rect.y: centre.y + centre.height + 8
        date: clock.date
    }

    BatteryPopup {
        id: batteryPopup
        anchor.window: bar
        anchor.rect.x: right.x + right.width - implicitWidth
        anchor.rect.y: right.y + right.height + 8
    }
}
