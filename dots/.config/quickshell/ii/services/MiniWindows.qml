pragma Singleton
pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Hyprland
import Quickshell.Io

/**
 * Mini windows: a window made small, out of the way, and back to full size with a click.
 *
 * With hyprland-plus, Hyprland does it itself (hl.dsp.window.mini): the window floats, shrinks to
 * binds:mini_width × mini_height where it was, can be moved anywhere and stays small, and a click on it brings it
 * back. hyprland-plus reports a `mini` flag on every window, which is how this knows.
 *
 * On stock Hyprland the shell does it: the window floats (if it was tiled), and glides to a row of mini windows in
 * the bottom right corner of its monitor; a click on one (the title bar's zone over it) brings it back to where and
 * how big it was, and tiles it again if it was tiled.
 *
 * Used by the floating windows' title bars (the down arrow), the bar's window buttons and Super + Ctrl + N
 * (`qs ipc call miniWindows toggleActive` on stock Hyprland), so all of them share one state.
 */
Singleton {
    id: root

    readonly property int miniWidth: 240
    readonly property int miniHeight: 150
    readonly property int miniGap: 10
    readonly property int moveDuration: 320

    // Stock Hyprland only: address -> { x, y, width, height, monitor, wasTiled }, what it was before.
    property var minis: ({})
    property var tweens: []

    // The focused window's address, as the window list writes it (Quickshell's toplevel leaves out the 0x).
    readonly property string activeAddress: {
        const address = Hyprland.activeToplevel?.address ?? "";
        if (address === "")
            return "";
        return address.startsWith("0x") ? address : `0x${address}`;
    }

    // Called at start-up so the singleton exists from the start: Quickshell makes one only when it is first used.
    function load() {}

    function window(address) {
        return HyprlandData.windowByAddress[address] ?? null;
    }

    // hyprland-plus reports `mini` on every window; stock Hyprland doesn't.
    function hasApi(address) {
        return (root.window(address)?.mini) !== undefined;
    }

    function isMini(address) {
        return root.hasApi(address) ? root.window(address)?.mini === true : root.minis[address] !== undefined;
    }

    function monitorOf(win) {
        return HyprlandData.monitors.find(m => m.id === win?.monitor) ?? null;
    }

    function toggle(address) {
        if (root.isMini(address))
            root.expand(address);
        else
            root.minimize(address);
    }

    function toggleActive() {
        if (root.activeAddress !== "")
            root.toggle(root.activeAddress);
    }

    function minimize(address) {
        const win = root.window(address);
        if (!win || win.fullscreen)
            return;
        if (root.hasApi(address)) {
            Hyprland.dispatch(`hl.dsp.window.mini({ action = "enable", window = "address:${address}" })`);
            return;
        }
        const monitor = root.monitorOf(win);
        if (!monitor)
            return;
        const wasTiled = !win.floating;
        if (wasTiled)
            Hyprland.dispatch(`hl.dsp.window.float({ action = "enable", window = "address:${address}" })`);
        const origin = { x: win.at[0], y: win.at[1], width: win.size[0], height: win.size[1], monitor: monitor.id, wasTiled: wasTiled };
        const others = Object.keys(root.minis).filter(a => root.minis[a].monitor === monitor.id).length;
        const right = monitor.x + monitor.width / monitor.scale;
        const bottom = monitor.y + monitor.height / monitor.scale;
        const x = right - root.miniGap - (others + 1) * (root.miniWidth + root.miniGap);
        const y = bottom - root.miniHeight - root.miniGap;
        const copy = Object.assign({}, root.minis);
        copy[address] = origin;
        root.minis = copy;
        root.animate(address, [win.at[0], win.at[1], win.size[0], win.size[1]], [x, y, root.miniWidth, root.miniHeight]);
    }

    function expand(address) {
        if (root.hasApi(address)) {
            Hyprland.dispatch(`hl.dsp.window.mini({ action = "disable", window = "address:${address}" })`);
            return;
        }
        const origin = root.minis[address];
        if (!origin)
            return;
        const copy = Object.assign({}, root.minis);
        delete copy[address];
        root.minis = copy;
        if (origin.wasTiled) {
            // It goes back into its tile; the layout decides where.
            root.cancelTween(address);
            Hyprland.dispatch(`hl.dsp.window.float({ action = "disable", window = "address:${address}" })`);
            return;
        }
        // Read fresh: the window list can lag the mini move that just happened.
        const now = root.window(address);
        const from = now ? [now.at[0], now.at[1], now.size[0], now.size[1]] : [origin.x, origin.y, root.miniWidth, root.miniHeight];
        root.animate(address, from, [origin.x, origin.y, origin.width, origin.height]);
    }

    function moveWindow(address, x, y) {
        Hyprland.dispatch(`hl.dsp.window.move({ x = ${Math.round(x)}, y = ${Math.round(y)}, relative = false, window = "address:${address}" })`);
    }

    function resizeWindow(address, width, height) {
        Hyprland.dispatch(`hl.dsp.window.resize({ x = ${Math.round(width)}, y = ${Math.round(height)}, relative = false, window = "address:${address}" })`);
    }

    // Eased moves follow the average of a sine curve and a cubic Bezier curve, so they start and stop gently, and
    // the size and place change together rather than the size snapping first.
    function sineEase(t) {
        return (1 - Math.cos(Math.PI * t)) / 2;
    }

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

    function ease(t) {
        return (root.sineEase(t) + root.bezierEase(t)) / 2;
    }

    function animate(address, from, to) {
        root.cancelTween(address);
        root.tweens = root.tweens.concat([{ address: address, from: from, to: to, start: Date.now() }]);
        tweenTimer.restart();
    }

    function cancelTween(address) {
        root.tweens = root.tweens.filter(tween => tween.address !== address);
    }

    IpcHandler {
        target: "miniWindows"

        function toggleActive(): void {
            root.toggleActive();
        }
        function expandAll(): void {
            Object.keys(root.minis).forEach(address => root.expand(address));
        }
    }

    // A window that closed while mini is forgotten.
    Connections {
        target: HyprlandData
        function onWindowListChanged() {
            const gone = Object.keys(root.minis).filter(address => !root.window(address));
            if (gone.length === 0)
                return;
            const copy = Object.assign({}, root.minis);
            gone.forEach(address => delete copy[address]);
            root.minis = copy;
        }
    }

    Timer {
        id: tweenTimer
        interval: 16
        repeat: true
        onTriggered: {
            const now = Date.now();
            root.tweens.forEach(tween => {
                const e = root.ease(Math.min(1, (now - tween.start) / root.moveDuration));
                const at = i => Math.round(tween.from[i] + (tween.to[i] - tween.from[i]) * e);
                root.resizeWindow(tween.address, at(2), at(3));
                root.moveWindow(tween.address, at(0), at(1));
            });
            root.tweens = root.tweens.filter(tween => now - tween.start < root.moveDuration);
            if (root.tweens.length === 0)
                tweenTimer.stop();
        }
    }
}
