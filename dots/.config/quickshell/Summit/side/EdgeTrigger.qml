pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Wayland
import Quickshell.Hyprland
import qs.services

// Pushing the pointer against the right edge of the rightmost screen opens the side menu: a strip one pixel wide down
// that edge, which only listens for the pointer resting on it a moment (Settings: the delay, or off). Not over a
// fullscreen window (a game would lose it to every stray flick).
Scope {
    id: root
    // The screen furthest right (on one screen, that one).
    readonly property var rightmost: Quickshell.screens.reduce((best, s) => !best || s.x + s.width > best.x + best.width ? s : best, null)
    readonly property bool fullscreen: Hyprland.monitorFor(root.rightmost)?.activeWorkspace?.hasFullscreen ?? false

    LazyLoader {
        active: Prefs.edgeOpensMenu && root.rightmost !== null && !root.fullscreen

        PanelWindow {
            screen: root.rightmost
            color: "transparent"
            WlrLayershell.namespace: "summit-edge"
            WlrLayershell.layer: WlrLayer.Top
            exclusionMode: ExclusionMode.Ignore
            anchors { top: true; right: true; bottom: true }
            implicitWidth: 1

            MouseArea {
                anchors.fill: parent
                hoverEnabled: true
                onContainsMouseChanged: containsMouse ? dwell.restart() : dwell.stop()
                onClicked: SummitState.openSideMenu(root.rightmost)
            }
            Timer {
                id: dwell
                interval: Prefs.edgeDelay
                onTriggered: if (!SummitState.sideMenuOpen) SummitState.openSideMenu(root.rightmost)
            }
        }
    }
}
