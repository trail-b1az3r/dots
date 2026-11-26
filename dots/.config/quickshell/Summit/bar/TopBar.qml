pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.common
import qs.services
import qs.popups

// The top bar: three floating groups on the wallpaper. Left, the launcher, the brightness and the workspaces (and hypr
// mode's chip while it is on); centre, the date, time and weather; right, the tray, network, sound, battery, power
// and the side menu, which a click anywhere on that group opens (side/SideMenu.qml).
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
            // Scrolling the left of the bar changes the brightness, as in the Halcyon shell.
            onScrolled: delta => {
                Brightness.step(Brightness.forScreen(bar.modelData), delta > 0 ? 0.05 : -0.05);
                brightnessPopup.peek();
            }
        }
        BrightnessButton {
            visible: Prefs.brightnessButton
            screen: bar.modelData
            onPeek: brightnessPopup.peek()
            onToggled: brightnessPopup.toggle()
        }
        Workspaces {
            screen: bar.modelData
            anchors.verticalCenter: parent.verticalCenter
        }
        HyprChip {
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
        // The side menu, with how many notifications wait in it.
        BarButton {
            icon: Prefs.doNotDisturb ? "do_not_disturb_on" : Notifs.count > 0 ? "notifications_unread" : "notifications"
            label: Notifs.count > 0 ? String(Notifs.count) : ""
            active: SummitState.sideMenuOpen && SummitState.sideMenuScreen === bar.modelData
            onClicked: SummitState.toggleSideMenu(bar.modelData)
        }
        clickable: true
        onClicked: SummitState.toggleSideMenu(bar.modelData)
    }

    Calendar {
        id: calendar
        anchor.window: bar
        anchor.rect.x: centre.x + centre.width / 2 - implicitWidth / 2
        anchor.rect.y: centre.y + centre.height + 8
        date: clock.date
    }

    BrightnessPopup {
        id: brightnessPopup
        screen: bar.modelData
        anchor.window: bar
        anchor.rect.x: left.x
        anchor.rect.y: left.y + left.height + 8
    }

    // Keep awake (the side menu's toggle): an idle inhibitor needs a window that is showing; the first screen's bar.
    IdleInhibitor {
        window: bar
        enabled: SummitState.keepAwake && bar.modelData === Quickshell.screens[0]
    }

    BatteryPopup {
        id: batteryPopup
        anchor.window: bar
        anchor.rect.x: right.x + right.width - implicitWidth
        anchor.rect.y: right.y + right.height + 8
    }
}
