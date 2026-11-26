pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Wayland
import Quickshell.Hyprland
import qs.common
import qs.services

// The side menu: what the Halcyon shell's right sidebar has, on frosted glass down the right of the screen. From the
// top: uptime with reload, settings and power; the brightness, volume and microphone sliders; the quick toggles;
// the notifications; and the calendar, to-do list and timer. Wi-Fi, Bluetooth and sound open pages of their own.
//
// Opens from a click on the bar's right group, or by pushing the pointer against the right edge of the rightmost
// screen (EdgeTrigger.qml); closes with a click outside it, Esc, or the same click again. It slides in from the edge.
Scope {
    id: root

    property bool shown: SummitState.sideMenuOpen
    // 0 in place .. 1 off the edge.
    property real away: 1
    onShownChanged: {
        if (shown) {
            slideOut.stop();
            slideIn.restart();
        } else {
            slideIn.stop();
            slideOut.restart();
        }
    }
    NumberAnimation { id: slideIn; target: root; property: "away"; to: 0; duration: Theme.enterMs + 60; easing.type: Easing.OutQuint }
    NumberAnimation { id: slideOut; target: root; property: "away"; to: 1; duration: 260; easing.type: Easing.InCubic }

    Binding {
        target: Network
        property: "watching"
        value: root.shown
    }

    LazyLoader {
        active: root.shown || root.away < 1

        PanelWindow {
            id: panel
            screen: SummitState.sideMenuScreen ?? Quickshell.screens[Quickshell.screens.length - 1]
            color: "transparent"
            WlrLayershell.namespace: "summit-sidemenu"
            WlrLayershell.layer: WlrLayer.Overlay
            WlrLayershell.keyboardFocus: root.shown ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None
            anchors { top: true; right: true; bottom: true }
            margins { top: Theme.gap; right: Theme.gap; bottom: Theme.gap }
            exclusiveZone: 0
            implicitWidth: 430
            mask: Region { item: card }

            // A click anywhere else closes it.
            HyprlandFocusGrab {
                windows: [panel]
                active: root.shown
                onCleared: SummitState.sideMenuOpen = false
            }

            Glass {
                id: card
                width: parent.width
                height: parent.height
                x: root.away * (parent.width + Theme.gap * 2)
                opacity: 1 - root.away * 0.6
                radius: Theme.radius + 8
                tint: Theme.glassTint + 0.22
                clip: true
                focus: true
                Keys.onEscapePressed: {
                    if (SummitState.sideMenuPage !== "")
                        SummitState.sideMenuPage = "";
                    else
                        SummitState.sideMenuOpen = false;
                }

                // The main page; a sub-page slides over it from the right.
                Item {
                    id: main
                    y: 12
                    width: parent.width - 24
                    height: parent.height - 24
                    x: SummitState.sideMenuPage === "" ? 12 : 12 - width * 0.25
                    Behavior on x { NumberAnimation { duration: Theme.enterMs; easing.type: Easing.OutQuint } }
                    opacity: SummitState.sideMenuPage === "" ? 1 : 0
                    Behavior on opacity { NumberAnimation { duration: Theme.animMs } }

                    Header {
                        id: header
                        width: parent.width
                        onCloseRequested: SummitState.sideMenuOpen = false
                    }
                    Sliders {
                        id: sliders
                        anchors.top: header.bottom
                        anchors.topMargin: 10
                        width: parent.width
                        screen: panel.screen
                    }
                    Toggles {
                        id: toggles
                        anchors.top: sliders.bottom
                        anchors.topMargin: 10
                        width: parent.width
                        onPageRequested: page => SummitState.sideMenuPage = page
                        onCloseRequested: SummitState.sideMenuOpen = false
                    }
                    NotificationList {
                        anchors.top: toggles.bottom
                        anchors.topMargin: 10
                        anchors.bottom: bottom.top
                        anchors.bottomMargin: 10
                        width: parent.width
                    }
                    BottomGroup {
                        id: bottom
                        anchors.bottom: parent.bottom
                        width: parent.width
                        height: implicitHeight
                    }
                }

                Item {
                    id: sub
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.margins: 12
                    width: parent.width - 24
                    x: SummitState.sideMenuPage === "" ? parent.width : 12
                    Behavior on x { NumberAnimation { duration: Theme.enterMs; easing.type: Easing.OutQuint } }
                    // The last page stays drawn while it slides away.
                    property string page: ""
                    Connections {
                        target: State
                        function onSideMenuPageChanged() { if (SummitState.sideMenuPage !== "") sub.page = SummitState.sideMenuPage; }
                    }
                    Loader {
                        anchors.fill: parent
                        active: sub.page !== ""
                        sourceComponent: sub.page === "wifi" ? wifi : sub.page === "bluetooth" ? bluetooth : sound
                    }
                    Component { id: wifi; WifiPage { onBack: SummitState.sideMenuPage = "" } }
                    Component { id: bluetooth; BluetoothPage { onBack: SummitState.sideMenuPage = "" } }
                    Component { id: sound; SoundPage { onBack: SummitState.sideMenuPage = "" } }
                }
            }
        }
    }
}
