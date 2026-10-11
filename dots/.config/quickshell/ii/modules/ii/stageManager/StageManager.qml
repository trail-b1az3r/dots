import qs
import qs.services
import qs.modules.common
import qs.modules.common.widgets
import qs.modules.common.functions
import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Hyprland
import Quickshell.Wayland

/**
 * Stage Manager: the windows that aren't in front are kept in a strip down the
 * left edge, as live previews. Click one to bring it forward. Off by default;
 * Settings > Interface > Stage manager turns it on.
 *
 * The strip reserves its width on the left, so tiled windows are laid out to
 * its right and don't go under it. Floating windows are not moved.
 *
 * Settings can also include windows on other workspaces, and windows on other
 * monitors (shown in one strip, on the focused monitor). Previews refresh at
 * the chosen rate, 18 frames a second by default and up to 50.
 */
Scope {
    id: root

    readonly property int stripWidth: 180
    readonly property int cardHeight: 128
    readonly property int previewFps: Math.min(50, Math.max(1, Config.options.stageManager.previewFps))
    readonly property string settingsTitle: "Halcyon Settings"

    function isShellWindow(win) {
        return win.title === root.settingsTitle || String(win.class ?? "").toLowerCase().includes("quickshell");
    }

    // Whether a window is on the workspace its monitor is showing.
    function onActiveWorkspace(win) {
        const monitor = HyprlandData.monitors.find(m => m.id === win.monitor);
        return monitor !== undefined && win.workspace?.id === monitor.activeWorkspace?.id;
    }

    Variants {
        model: Quickshell.screens

        PanelWindow {
            id: strip

            required property var modelData
            screen: modelData

            readonly property HyprlandMonitor hyprMonitor: Hyprland.monitorFor(modelData)
            readonly property bool focusedHere: hyprMonitor?.id === Hyprland.focusedMonitor?.id
            // A fullscreen app or video takes the screen, so the strip steps aside.
            readonly property bool fullscreenHere: HyprlandData.fullscreenOnMonitor(modelData.name)
            // With cross-monitor windows there is one strip, on the focused monitor; otherwise one per monitor.
            readonly property bool showHere: Config.options.stageManager.enable && !fullscreenHere
                && (!Config.options.stageManager.crossMonitor || focusedHere)
            readonly property var stashed: HyprlandData.windowList.filter(win =>
                (Config.options.stageManager.crossMonitor || win.monitor === hyprMonitor?.id)
                && (Config.options.stageManager.crossWorkspace || root.onActiveWorkspace(win))
                && win.address !== Hyprland.activeToplevel?.address
                && !root.isShellWindow(win))

            visible: showHere
            anchors {
                top: true
                bottom: true
                left: true
            }
            implicitWidth: root.stripWidth
            // Tiled windows are laid out to the right of the strip.
            exclusionMode: visible ? ExclusionMode.Normal : ExclusionMode.Ignore
            exclusiveZone: root.stripWidth
            color: "transparent"
            WlrLayershell.namespace: "quickshell:stageManager"
            WlrLayershell.layer: WlrLayer.Top
            WlrLayershell.keyboardFocus: WlrKeyboardFocus.None

            // Only the cards take input; the rest of the strip lets clicks through.
            mask: Region {
                item: cards
            }

            Rectangle {
                anchors.fill: parent
                radius: Appearance.rounding.normal
                color: ColorUtils.transparentize(Appearance.colors.colLayer0, 0.25)
                border.width: 1
                border.color: Appearance.colors.colLayer0Border
            }

            // Captures a frame of every preview at the chosen rate, rather than live feeds.
            Timer {
                interval: Math.round(1000 / root.previewFps)
                repeat: true
                running: strip.showHere && strip.stashed.length > 0
                onTriggered: {
                    for (let i = 0; i < previews.count; i++)
                        previews.itemAt(i)?.refreshPreview();
                }
            }

            ColumnLayout {
                id: cards
                anchors {
                    top: parent.top
                    left: parent.left
                    right: parent.right
                    margins: 6
                }
                spacing: 8

                Repeater {
                    id: previews
                    model: strip.stashed

                    delegate: Item {
                        id: card

                        required property var modelData
                        readonly property var win: modelData
                        // Found by address, so the preview follows the same window Hyprland reports.
                        readonly property var toplevel: ToplevelManager.toplevels.values.find(
                            t => `0x${t.HyprlandToplevel?.address}` === card.win.address) ?? null

                        function refreshPreview() {
                            view.captureFrame();
                        }

                        Component.onCompleted: refreshPreview()

                        Layout.fillWidth: true
                        implicitHeight: root.cardHeight + titleText.implicitHeight + 6

                        Rectangle {
                            id: frame
                            anchors {
                                top: parent.top
                                left: parent.left
                                right: parent.right
                            }
                            height: root.cardHeight
                            radius: Appearance.rounding.small
                            color: Appearance.colors.colLayer1
                            clip: true

                            ScreencopyView {
                                id: view
                                anchors.fill: parent
                                anchors.margins: 3
                                captureSource: card.toplevel
                                live: false
                            }
                        }

                        StyledText {
                            id: titleText
                            anchors {
                                top: frame.bottom
                                topMargin: 6
                                left: parent.left
                                right: parent.right
                            }
                            text: card.win.title ?? ""
                            color: Appearance.colors.colOnLayer0
                            elide: Text.ElideRight
                            font.pixelSize: Appearance.font.pixelSize.small
                            horizontalAlignment: Text.AlignHCenter
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: Hyprland.dispatch(`hl.dsp.focus({ window = "address:${card.win.address}" })`)
                        }
                    }
                }
            }
        }
    }
}
