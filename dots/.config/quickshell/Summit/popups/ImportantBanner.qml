pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Wayland
import Quickshell.Hyprland
import qs.common
import qs.services

// An important notification (the importance model, services/Notifs.qml), under the clock on the focused screen: a
// small pill that opens out sideways into a line of glass with the app and the model's one-line summary, stays three
// seconds, and fades away; then the next one, if more came. Never over a fullscreen window. Clicking it does the
// notification's default action, or opens the side menu.
Scope {
    id: root
    readonly property var current: Notifs.banners[0] ?? null

    LazyLoader {
        active: root.current !== null

        PanelWindow {
            id: window
            screen: Quickshell.screens.find(s => s.name === Hyprland.focusedMonitor?.name) ?? Quickshell.screens[0]
            color: "transparent"
            WlrLayershell.namespace: "summit-banner"
            WlrLayershell.layer: WlrLayer.Overlay
            anchors.top: true
            margins.top: 6
            exclusiveZone: 0
            implicitWidth: Math.min(620, (screen?.width ?? 1400) - 80)
            implicitHeight: 52
            mask: Region { item: pill }

            readonly property var item: root.current
            readonly property real fullWidth: Math.min(width, row.implicitWidth + 36)
            property real openness: 0      // 0: the small pill; 1: all the way out
            property real shown: 0         // the pill's opacity

            onItemChanged: if (item) play.restart()
            Component.onCompleted: if (item) play.restart()

            SequentialAnimation {
                id: play
                ScriptAction { script: { window.openness = 0; window.shown = 0; pill.scale = 0.6; bar.width = 0; } }
                // In: the pill pops up under the clock...
                ParallelAnimation {
                    NumberAnimation { target: window; property: "shown"; to: 1; duration: 200; easing.type: Easing.OutCubic }
                    NumberAnimation { target: pill; property: "scale"; to: 1; duration: 320; easing.type: Easing.OutBack; easing.overshoot: 2.2 }
                }
                // ...and opens out sideways.
                NumberAnimation { target: window; property: "openness"; to: 1; duration: 520; easing.type: Easing.OutQuint }
                // Three seconds, the line under it running out.
                NumberAnimation { target: bar; property: "width"; from: 0; to: pill.width - 40; duration: 3000 }
                // Out: a fade, folding a little.
                ParallelAnimation {
                    NumberAnimation { target: window; property: "shown"; to: 0; duration: 420; easing.type: Easing.InCubic }
                    NumberAnimation { target: window; property: "openness"; to: 0.82; duration: 420; easing.type: Easing.InCubic }
                }
                ScriptAction { script: Notifs.nextBanner() }
            }

            Glass {
                id: pill
                anchors.horizontalCenter: parent.horizontalCenter
                y: 4
                height: 44
                width: 44 + (window.fullWidth - 44) * window.openness
                radius: height / 2
                tint: Theme.glassTint + 0.24
                opacity: window.shown
                clip: true

                Row {
                    id: row
                    x: 6
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 10
                    // The app's icon in a round accent badge.
                    Rectangle {
                        width: 32
                        height: 32
                        radius: 16
                        color: Theme.accent
                        anchors.verticalCenter: parent.verticalCenter
                        Image {
                            id: icon
                            anchors.centerIn: parent
                            width: 20
                            height: 20
                            source: {
                                const name = window.item?.icon ?? "";
                                return name === "" ? "" : name.startsWith("/") || name.includes("://") ? name : Quickshell.iconPath(name, true);
                            }
                            visible: status === Image.Ready
                            sourceSize: Qt.size(40, 40)
                        }
                        Symbol {
                            anchors.centerIn: parent
                            visible: !icon.visible
                            name: "priority_high"
                            fill: 1
                            color: Theme.accentText
                            size: 20
                        }
                    }
                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        // The words come in once the pill has opened past them.
                        opacity: Math.max(0, (window.openness - 0.45) / 0.55)
                        Text {
                            text: window.item?.app ?? ""
                            visible: text !== ""
                            color: Theme.muted
                            font.family: Theme.font
                            font.pixelSize: 10
                            font.weight: Font.DemiBold
                            font.letterSpacing: 0.6
                            font.capitalization: Font.AllUppercase
                        }
                        Text {
                            text: window.item?.summary ?? ""
                            color: Theme.text
                            font.family: Theme.font
                            font.pixelSize: 14
                            font.weight: Font.Medium
                            elide: Text.ElideRight
                            width: Math.min(implicitWidth, window.width - 100)
                        }
                    }
                }

                Rectangle {
                    id: bar
                    x: 20
                    anchors.bottom: parent.bottom
                    height: 2
                    radius: 1
                    color: Theme.alpha(Theme.accent, 0.8)
                    opacity: window.openness
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        const n = window.item?.notification;
                        const action = (n?.actions ?? []).find(a => a.identifier === "default");
                        if (action)
                            action.invoke();
                        else
                            SummitState.openSideMenu(window.screen);
                        play.stop();
                        Notifs.nextBanner();
                    }
                }
            }
        }
    }
}
