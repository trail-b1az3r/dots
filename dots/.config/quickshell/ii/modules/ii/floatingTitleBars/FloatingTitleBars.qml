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
 * Hyprland 0.56 draws no title bars. Each floating window on a monitor gets a
 * bar above it, with its buttons:
 *   - the headphones mute the window's sound (the cable is pulled out when muted);
 *   - the down arrow makes the window a mini window: a small one in the bottom
 *     right corner. Hovering a mini window brings it back to full size;
 *   - the close button closes it.
 *
 * Bars are drawn on one full-screen overlay per monitor. The overlay takes input
 * only where the bars and the mini windows' hover zones are, so the pointer's
 * position stays put while a window moves underneath it.
 *
 * While a bar is dragged it follows the pointer itself, rather than waiting for
 * Hyprland's next window list. The shell's own windows (Settings) never get one.
 *
 * Other apps that draw their own title bar are listed in Settings > Interface >
 * Floating windows, since Hyprland doesn't say which apps do.
 */
Scope {
    id: root

    readonly property int barHeight: 26
    readonly property int miniWidth: 240
    readonly property int miniHeight: 150
    readonly property int miniGap: 10
    // Windows the shell opens for itself; they keep their own frame.
    readonly property string settingsTitle: "Halcyon Settings"

    // Mini windows: address -> the size and place they had before, and their monitor.
    property var minis: ({})

    function isShellWindow(win) {
        return win.title === root.settingsTitle || String(win.class ?? "").toLowerCase().includes("quickshell");
    }

    // The audio streams that belong to a window's process.
    function audioStreams(win) {
        return Audio.outputAppNodes.filter(node => node.audio && node.properties["application.process.id"] == win.pid);
    }

    function isMuted(win) {
        const streams = root.audioStreams(win);
        return streams.length > 0 && streams.every(node => node.audio.muted);
    }

    function setMuted(win, muted) {
        root.audioStreams(win).forEach(node => {
            node.audio.muted = muted;
        });
    }

    function moveWindow(address, x, y) {
        Hyprland.dispatch(`hl.dsp.window.move({ x = ${Math.round(x)}, y = ${Math.round(y)}, relative = false, window = "address:${address}" })`);
    }

    function resizeWindow(address, width, height) {
        Hyprland.dispatch(`hl.dsp.window.resize({ x = ${Math.round(width)}, y = ${Math.round(height)}, relative = false, window = "address:${address}" })`);
    }

    // Makes a window a mini window in the bottom right corner of its monitor, next to any others.
    function minimize(win, monitor) {
        const origin = { x: win.at[0], y: win.at[1], width: win.size[0], height: win.size[1], monitor: monitor.id };
        const others = Object.keys(root.minis).filter(address => root.minis[address].monitor === monitor.id).length;
        const right = monitor.x + monitor.width / monitor.scale;
        const bottom = monitor.y + monitor.height / monitor.scale;
        const x = right - root.miniGap - (others + 1) * (root.miniWidth + root.miniGap);
        const y = bottom - root.miniHeight - root.miniGap;
        const copy = Object.assign({}, root.minis);
        copy[win.address] = origin;
        root.minis = copy;
        root.resizeWindow(win.address, root.miniWidth, root.miniHeight);
        root.moveWindow(win.address, x, y);
    }

    // Brings a mini window back to the size and place it had before.
    function expand(address) {
        const origin = root.minis[address];
        if (!origin)
            return;
        const copy = Object.assign({}, root.minis);
        delete copy[address];
        root.minis = copy;
        root.resizeWindow(address, origin.width, origin.height);
        root.moveWindow(address, origin.x, origin.y);
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

            // Input goes only to the bars and to the hover zones of mini windows.
            mask: Region {
                regions: Array.from({ length: bars.count }, (_, i) =>
                    regionComponent.createObject(overlay, { item: bars.itemAt(i) }))
                    .concat(Array.from({ length: bars.count }, (_, i) =>
                        regionComponent.createObject(overlay, { item: bars.itemAt(i)?.hoverZone })))
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
                        readonly property bool isMini: root.minis[win.address] !== undefined
                        readonly property bool muted: root.isMuted(win)
                        readonly property bool hasSound: root.audioStreams(win).length > 0
                        // Set in the drag: the position asked of Hyprland, shown until its window list catches up.
                        property bool moving: false
                        property real movedX: 0
                        property real movedY: 0
                        readonly property real shownX: moving ? movedX : win.at[0]
                        readonly property real shownY: moving ? movedY : win.at[1]
                        readonly property Item hoverZone: zone

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

                        // Under a mini window the body is covered, so hovering it brings the window back.
                        Item {
                            id: zone
                            x: 0
                            y: root.barHeight
                            width: bar.width
                            height: bar.isMini ? bar.win.size[1] : 0
                            visible: bar.isMini

                            MouseArea {
                                anchors.fill: parent
                                hoverEnabled: true
                                onEntered: root.expand(bar.win.address)
                            }
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
                                right: buttons.left
                                verticalCenter: parent.verticalCenter
                                leftMargin: 8
                                rightMargin: 4
                            }
                            text: bar.win.title ?? ""
                            color: Appearance.colors.colOnLayer0
                            elide: Text.ElideRight
                            font.pixelSize: Appearance.font.pixelSize.small
                        }

                        // The buttons sit above the drag area, so they get their own clicks.
                        Row {
                            id: buttons
                            z: 2
                            anchors {
                                right: parent.right
                                verticalCenter: parent.verticalCenter
                                rightMargin: 4
                            }
                            spacing: 2

                            // Mute: the headphones are plugged in while the window has sound, and unplugged when muted.
                            Item {
                                width: 20
                                height: 20
                                opacity: bar.hasSound ? 1 : 0.4

                                CustomIcon {
                                    anchors.centerIn: parent
                                    width: 16
                                    height: 16
                                    source: bar.muted ? "headphones-unplugged-symbolic" : "headphones-symbolic"
                                    colorize: true
                                    color: Appearance.colors.colOnLayer0
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: root.setMuted(bar.win, !bar.muted)
                                    StyledToolTip {
                                        text: bar.hasSound ? (bar.muted ? Translation.tr("Unmute this window") : Translation.tr("Mute this window"))
                                                           : Translation.tr("This window has no sound")
                                    }
                                }
                            }

                            // Minimise: down arrow to make a mini window; clicking a mini window's bar brings it back.
                            Item {
                                width: 20
                                height: 20

                                CustomIcon {
                                    anchors.centerIn: parent
                                    width: 16
                                    height: 16
                                    source: "halcyon-minimize-symbolic"
                                    colorize: true
                                    color: Appearance.colors.colOnLayer0
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: bar.isMini ? root.expand(bar.win.address) : root.minimize(bar.win, overlay.monitorInfo)
                                    StyledToolTip {
                                        text: bar.isMini ? Translation.tr("Bring back to full size") : Translation.tr("Make a mini window")
                                    }
                                }
                            }

                            Item {
                                width: 20
                                height: 20

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
                                const x = mover.windowX + p.x - mover.startX;
                                const y = mover.windowY + p.y - mover.startY;
                                bar.movedX = x;
                                bar.movedY = y;
                                root.moveWindow(bar.win.address, x, y);
                            }

                            onReleased: settle.restart()
                        }
                    }
                }
            }
        }
    }
}
