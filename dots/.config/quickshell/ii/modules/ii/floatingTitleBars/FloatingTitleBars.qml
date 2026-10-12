import qs
import qs.services
import qs.modules.common
import qs.modules.common.widgets
import QtQuick
import Quickshell
import Quickshell.Hyprland
import Quickshell.Io
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

    // A tiled window that a press in its top band turns floating (an app's own title bar starts a move,
    // or a drag does): Hyprland centres it on the cursor, which is the jump. While such a window floats,
    // it is kept where it was grabbed: the tile's place, moved by the same amount as the cursor.
    readonly property int grabBand: 140
    readonly property int grabTimeout: 4000
    // address -> { x, y, w, h } for each window while it is tiled
    property var tileGeometry: ({})
    // The window being kept: { address, tile, startX, startY, started }, startX null until the cursor is read
    property var grab: null

    Connections {
        target: HyprlandData

        function onWindowListChanged() {
            const previous = root.tileGeometry;
            const tiles = Object.assign({}, previous);
            HyprlandData.windowList.forEach(win => {
                if (!win.floating)
                    tiles[win.address] = { x: win.at[0], y: win.at[1], w: win.size[0], h: win.size[1] };
            });
            root.tileGeometry = tiles;

            if (!Config.options.floatingTitleBars.keepTileGrab || root.grab !== null)
                return;
            // A window that was tiled and is now floating has just been turned floating.
            const turned = HyprlandData.windowList.find(win => win.floating && previous[win.address] !== undefined);
            if (turned) {
                root.grab = { address: turned.address, tile: previous[turned.address], startX: null, startY: null, started: Date.now() };
                cursorPoll.running = true;
            }
        }
    }

    // Reads the cursor's position from Hyprland, with the grab's own timing.
    Process {
        id: cursorPoll
        command: ["hyprctl", "cursorpos"]
        stdout: StdioCollector {
            onStreamFinished: root.onCursor(this.text)
        }
    }

    Timer {
        interval: 30
        repeat: true
        running: root.grab !== null
        onTriggered: cursorPoll.running = true
    }

    function onCursor(text) {
        const grab = root.grab;
        if (grab === null)
            return;
        const m = text.trim().match(/^(-?\d+),\s*(-?\d+)/);
        if (!m)
            return;
        const cx = Number(m[1]);
        const cy = Number(m[2]);
        const win = HyprlandData.windowByAddress[grab.address];
        // The grab is over once the window has tiled again (Hyprland puts it back on release), or after a while.
        if (!win || !win.floating || Date.now() - grab.started > root.grabTimeout) {
            root.grab = null;
            return;
        }
        if (grab.startX === null) {
            const tile = grab.tile;
            const inBand = cx >= tile.x && cx < tile.x + tile.w && cy >= tile.y && cy < tile.y + root.grabBand;
            if (!inBand) {
                // Not a press in the top band: leave Hyprland to it.
                root.grab = null;
                return;
            }
            root.grab = Object.assign({}, grab, { startX: cx, startY: cy });
            root.resizeWindow(grab.address, tile.w, tile.h);
            return;
        }
        root.moveWindow(grab.address, grab.tile.x + (cx - grab.startX), grab.tile.y + (cy - grab.startY));
    }

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

    // Eased moves: a window moved to its mini place, or back to its full place, follows the
    // average of a sine curve and a cubic Bezier curve, so it starts and stops gently.
    readonly property int moveDuration: 320
    property var tweens: []

    function sineEase(t) {
        return (1 - Math.cos(Math.PI * t)) / 2;
    }

    // Cubic Bezier from (0, 0) to (1, 1), control points (0.4, 0) and (0.2, 1): find the
    // curve's parameter for this time by bisection, then read the height there.
    function bezierEase(t) {
        const x = s => 3 * (1 - s) * (1 - s) * s * 0.4 + 3 * (1 - s) * s * s * 0.2 + s * s * s;
        const y = s => 3 * (1 - s) * s * s + s * s * s;
        let low = 0;
        let high = 1;
        for (let i = 0; i < 24; i++) {
            const mid = (low + high) / 2;
            if (x(mid) < t)
                low = mid;
            else
                high = mid;
        }
        return y((low + high) / 2);
    }

    function moveEase(t) {
        return (root.sineEase(t) + root.bezierEase(t)) / 2;
    }

    // Moves a window from one place and size to another over the same curve, so its size and place
    // change together rather than the size snapping first.
    function animateWindow(address, from, to) {
        root.cancelTween(address);
        root.tweens = root.tweens.concat([{ address: address, from: from, to: to, start: Date.now() }]);
        tweenTimer.restart();
    }

    function cancelTween(address) {
        root.tweens = root.tweens.filter(tween => tween.address !== address);
    }

    Timer {
        id: tweenTimer
        interval: 16
        repeat: true
        onTriggered: {
            const now = Date.now();
            root.tweens.forEach(tween => {
                const e = root.moveEase(Math.min(1, (now - tween.start) / root.moveDuration));
                const at = i => Math.round(tween.from[i] + (tween.to[i] - tween.from[i]) * e);
                root.resizeWindow(tween.address, at(2), at(3));
                root.moveWindow(tween.address, at(0), at(1));
            });
            root.tweens = root.tweens.filter(tween => now - tween.start < root.moveDuration);
            if (root.tweens.length === 0)
                tweenTimer.stop();
        }
    }

    // The window's position, kept so the window and its bar stay on the monitor: the bar
    // is always visible, and the window never goes off the edge.
    function clampToMonitor(win, monitor, x, y) {
        if (!monitor)
            return { x: x, y: y };
        const left = monitor.x;
        const top = monitor.y + root.barHeight;
        const right = monitor.x + monitor.width / monitor.scale - win.size[0];
        const bottom = monitor.y + monitor.height / monitor.scale - win.size[1];
        return {
            x: Math.round(Math.min(Math.max(x, left), Math.max(left, right))),
            y: Math.round(Math.min(Math.max(y, top), Math.max(top, bottom)))
        };
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
        root.animateWindow(win.address, [win.at[0], win.at[1], win.size[0], win.size[1]],
            [x, y, root.miniWidth, root.miniHeight]);
    }

    // Brings a mini window back to the size and place it had before.
    function expand(address) {
        const origin = root.minis[address];
        if (!origin)
            return;
        const copy = Object.assign({}, root.minis);
        delete copy[address];
        root.minis = copy;
        // Read fresh: the window list can lag the mini move that just happened.
        const now = HyprlandData.windowByAddress[address] ?? null;
        const from = now ? [now.at[0], now.at[1], now.size[0], now.size[1]] : [origin.x, origin.y, root.miniWidth, root.miniHeight];
        root.animateWindow(address, from, [origin.x, origin.y, origin.width, origin.height]);
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
                            property bool dragging: false

                            onPressed: mouse => {
                                // A drag takes over from any move still easing.
                                root.cancelTween(bar.win.address);
                                const p = mapToItem(stage, mouse.x, mouse.y);
                                // The window's place now, not the one the list had before the last move.
                                const fresh = HyprlandData.windowByAddress[bar.win.address] ?? bar.win;
                                mover.startX = p.x;
                                mover.startY = p.y;
                                mover.windowX = fresh.at[0];
                                mover.windowY = fresh.at[1];
                                mover.dragging = false;
                            }

                            // The bar only starts following once the pointer really moves, so a click doesn't move the window.
                            onPositionChanged: mouse => {
                                if (!mover.pressed)
                                    return;
                                const p = mapToItem(stage, mouse.x, mouse.y);
                                if (!mover.dragging) {
                                    if (Math.abs(p.x - mover.startX) < 3 && Math.abs(p.y - mover.startY) < 3)
                                        return;
                                    mover.dragging = true;
                                    settle.stop();
                                    bar.moving = true;
                                }
                                const target = root.clampToMonitor(bar.win, overlay.monitorInfo,
                                    mover.windowX + p.x - mover.startX, mover.windowY + p.y - mover.startY);
                                bar.movedX = target.x;
                                bar.movedY = target.y;
                                root.moveWindow(bar.win.address, target.x, target.y);
                            }

                            // A click without a drag focuses the window; the end of a drag hands the position back to Hyprland.
                            onReleased: {
                                if (!mover.dragging)
                                    Hyprland.dispatch(`hl.dsp.focus({ window = "address:${bar.win.address}" })`);
                                mover.dragging = false;
                                if (bar.moving)
                                    settle.restart();
                            }
                        }
                    }
                }
            }
        }
    }
}
