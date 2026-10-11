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
 * Stage Manager: the windows on the current workspace that aren't in front
 * are kept in a strip down the left edge as live previews. Click one to bring
 * it forward. Off by default; Settings > Interface > Stage manager turns it on.
 *
 * The strip sits over the left edge of the screen rather than shrinking the
 * windows, so the windows underneath it stay where they are.
 */
Scope {
    id: root

    readonly property int stripWidth: 180
    readonly property int cardHeight: 110
    readonly property string settingsTitle: "illogical-impulse Settings"

    Variants {
        model: Quickshell.screens

        PanelWindow {
            id: strip

            required property var modelData
            screen: modelData

            readonly property HyprlandMonitor hyprMonitor: Hyprland.monitorFor(modelData)
            readonly property var monitorInfo: HyprlandData.monitors.find(m => m.id === hyprMonitor?.id) ?? null
            // Other windows on this monitor's active workspace: not the one in front, not the shell's own.
            readonly property var stashed: monitorInfo ? HyprlandData.windowList.filter(win =>
                win.monitor === hyprMonitor.id
                && win.workspace?.id === monitorInfo.activeWorkspace?.id
                && win.address !== Hyprland.activeToplevel?.address
                && win.title !== root.settingsTitle
                && !String(win.class ?? "").toLowerCase().includes("quickshell")) : []

            visible: Config.options.stageManager.enable && stashed.length > 0
            anchors {
                top: true
                bottom: true
                left: true
            }
            implicitWidth: root.stripWidth
            exclusionMode: ExclusionMode.Ignore
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

            ColumnLayout {
                id: cards
                anchors {
                    top: parent.top
                    left: parent.left
                    right: parent.right
                    margins: 8
                }
                spacing: 8

                Repeater {
                    model: strip.stashed

                    delegate: Item {
                        id: card

                        required property var modelData
                        readonly property var win: modelData
                        // Found by address, so the preview follows the same window Hyprland reports.
                        readonly property var toplevel: ToplevelManager.toplevels.values.find(
                            t => `0x${t.HyprlandToplevel?.address}` === card.win.address) ?? null

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
                                anchors.fill: parent
                                anchors.margins: 4
                                captureSource: card.toplevel
                                live: true
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
