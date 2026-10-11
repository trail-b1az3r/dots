import qs
import qs.services
import qs.modules.common
import qs.modules.common.widgets
import QtQuick
import Quickshell
import Quickshell.Hyprland
import Quickshell.Wayland

/**
 * Title bars for floating windows, drawn by the shell.
 *
 * Hyprland 0.56 draws no title bars. Each floating window on a monitor gets
 * a bar above it: drag the bar to move the window, click the close button to
 * close it. Bars are drawn on one full-screen overlay per monitor. The overlay
 * takes input only where the bars are, so the pointer's position stays put
 * while the window moves underneath it.
 *
 * While a bar is dragged it follows the pointer itself, rather than waiting for
 * Hyprland's next window list, so it stays with the window. The shell's own
 * windows (Settings) never get one.
 *
 * Other apps that draw their own title bar are listed in Settings > Interface >
 * Floating windows, since Hyprland doesn't say which apps do.
 */
Scope {
    id: root

    readonly property int barHeight: 26
    // Windows the shell opens for itself; they keep their own frame.
    readonly property string settingsTitle: "illogical-impulse Settings"

    function isShellWindow(win) {
        return win.title === root.settingsTitle || String(win.class ?? "").toLowerCase().includes("quickshell");
    }

    Variants {
        model: Quickshell.screens

        PanelWindow {
            id: overlay

            required property var modelData
            screen: modelData

            readonly property HyprlandMonitor hyprMonitor: Hyprland.monitorFor(modelData)
            readonly property var monitorInfo: HyprlandData.monitors.find(m => m.id === hyprMonitor?.id) ?? null
            readonly property var skipped: Config.options.floatingTitleBars.skipClasses
                .split(",").map(name => name.trim().toLowerCase()).filter(name => name.length > 0)
            readonly property var floatingWindows: monitorInfo ? HyprlandData.windowList.filter(win =>
                win.floating && win.monitor === hyprMonitor.id
                && !root.isShellWindow(win)
                && !overlay.skipped.includes(String(win.class ?? "").toLowerCase())) : []

            visible: Config.options.floatingTitleBars.enable && floatingWindows.length > 0
            anchors {
                top: true
                bottom: true
                left: true
                right: true
            }
            exclusionMode: ExclusionMode.Ignore
            color: "transparent"
            WlrLayershell.namespace: "quickshell:floatingTitleBars"
            WlrLayershell.layer: WlrLayer.Top
            WlrLayershell.keyboardFocus: WlrKeyboardFocus.None

            Component {
                id: regionComponent
                Region {}
            }

            // Input goes only to the bars. Everything else passes through.
            mask: Region {
                regions: Array.from({ length: bars.count }, (_, i) =>
                    regionComponent.createObject(overlay, { item: bars.itemAt(i) }))
            }

            Item {
                id: stage
                anchors.fill: parent

                Repeater {
                    id: bars
                    model: overlay.floatingWindows

                    delegate: Item {
                        id: bar

                        required property var modelData
                        readonly property var win: modelData

                        // While the bar is being dragged it shows the position it asked
                        // Hyprland for. Otherwise it shows Hyprland's own position.
                        property bool moving: false
                        property real movedX: 0
                        property real movedY: 0
                        readonly property real shownX: moving ? movedX : win.at[0]
                        readonly property real shownY: moving ? movedY : win.at[1]

                        // Window and monitor positions are both global, so the difference is the offset on this screen.
                        x: shownX - overlay.monitorInfo.x
                        y: shownY - overlay.monitorInfo.y - root.barHeight
                        width: win.size[0]
                        height: root.barHeight

                        // Once the drag ends, hand the position back to Hyprland's window list.
                        // The delay covers the time Hyprland takes to apply the last move.
                        Timer {
                            id: settle
                            interval: 400
                            onTriggered: bar.moving = false
                        }

                        Rectangle {
                            anchors.fill: parent
                            radius: Appearance.rounding.small
                            color: Appearance.colors.colLayer0
                            border.width: 1
                            border.color: Appearance.colors.colLayer0Border
                        }

                        StyledText {
                            anchors {
                                left: parent.left
                                right: closeButton.left
                                verticalCenter: parent.verticalCenter
                                leftMargin: 8
                                rightMargin: 4
                            }
                            text: bar.win.title ?? ""
                            color: Appearance.colors.colOnLayer0
                            elide: Text.ElideRight
                            font.pixelSize: Appearance.font.pixelSize.small
                        }

                        // The close button sits above the drag area, so it gets its own clicks.
                        Item {
                            id: closeButton
                            anchors {
                                right: parent.right
                                verticalCenter: parent.verticalCenter
                                rightMargin: 4
                            }
                            width: 20
                            height: 20
                            z: 2

                            MaterialSymbol {
                                anchors.centerIn: parent
                                text: "close"
                                iconSize: 16
                                color: Appearance.colors.colOnLayer0
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: Hyprland.dispatch(`hl.dsp.window.close({ window = "address:${bar.win.address}" })`)
                            }
                        }

                        // Drag the bar to move the window. The pointer is measured in the
                        // overlay's own coordinates, which don't move with the window.
                        MouseArea {
                            id: mover
                            anchors.fill: parent
                            z: 1
                            cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor

                            property real startX: 0
                            property real startY: 0
                            property real windowX: 0
                            property real windowY: 0

                            onPressed: mouse => {
                                const p = mapToItem(stage, mouse.x, mouse.y);
                                mover.startX = p.x;
                                mover.startY = p.y;
                                mover.windowX = bar.win.at[0];
                                mover.windowY = bar.win.at[1];
                                settle.stop();
                                bar.movedX = mover.windowX;
                                bar.movedY = mover.windowY;
                                bar.moving = true;
                                Hyprland.dispatch(`hl.dsp.focus({ window = "address:${bar.win.address}" })`);
                            }

                            onPositionChanged: mouse => {
                                if (!mover.pressed)
                                    return;
                                const p = mapToItem(stage, mouse.x, mouse.y);
                                const x = Math.round(mover.windowX + p.x - mover.startX);
                                const y = Math.round(mover.windowY + p.y - mover.startY);
                                bar.movedX = x;
                                bar.movedY = y;
                                Hyprland.dispatch(`hl.dsp.window.move({ x = ${x}, y = ${y}, relative = false, window = "address:${bar.win.address}" })`);
                            }

                            onReleased: settle.restart()
                        }
                    }
                }
            }
        }
    }
}
