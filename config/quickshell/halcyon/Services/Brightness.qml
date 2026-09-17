pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import qs.Config

/**
 * The display and keyboard backlights.
 *
 * Read through `halcyon backlight status`, which handles both
 * brightnessctl and the sysfs fallback. Refreshed on demand rather than
 * on a timer: brightness only changes because something changed it, and
 * every path that does calls `refresh()`.
 */
Singleton {
    id: root

    property int percent: 0
    property bool available: false
    property string device: ""

    property int keyboardPercent: 0
    property bool keyboardAvailable: false

    readonly property string glyph: {
        if (root.percent < 25) return "󰃞";
        if (root.percent < 60) return "󰃟";
        return "󰃠";
    }

    function refresh(): void {
        reader.running = true;
    }

    function set(value: int): void {
        const clamped = Math.max(1, Math.min(100, Math.round(value)));
        root.percent = clamped;   // optimistic, so the HUD tracks the drag
        Quickshell.execDetached(Paths.command(["backlight", String(clamped)]));
        settle.restart();
    }

    function adjust(delta: int): void {
        root.set(root.percent + delta);
    }

    function setKeyboard(value: int): void {
        root.keyboardPercent = Math.max(0, Math.min(100, Math.round(value)));
        Quickshell.execDetached(
            Paths.command(["action", "keyboard.brightness",
                           "percent=" + String(root.keyboardPercent)])
        );
    }

    Process {
        id: reader
        command: Paths.command(["backlight", "status"])
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const payload = JSON.parse(this.text);
                    root.available = payload.available ?? false;
                    root.percent = payload.percent ?? 0;
                    root.device = payload.device ?? "";
                } catch (error) {
                    root.available = false;
                }
            }
        }
    }

    // After a drag, confirm what actually landed. The optimistic value is
    // right often enough to keep the HUD smooth and wrong often enough
    // (rounding, minimum steps) to be worth checking once.
    Timer {
        id: settle
        interval: 400
        onTriggered: root.refresh()
    }

    Component.onCompleted: root.refresh()
}
