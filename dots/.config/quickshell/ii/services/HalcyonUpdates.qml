pragma Singleton
pragma ComponentBehavior: Bound

import qs.modules.common
import qs.modules.common.functions
import QtQuick
import Quickshell
import Quickshell.Io

/**
 * Halcyon's own updates (the repository's main branch), as the updater (hypr/hyprland/halcyon/update) leaves them in
 * ~/.local/state/halcyon: how many commits are waiting, and the last problem. The bar's update button and the
 * sidebar's Update Halcyon button read this, and apply() runs `update apply`.
 *
 * The hourly systemd timer is what checks; the shell also checks a little after it starts, so an install without the
 * timer (or with it off) still hears about updates. The updater runs through bash: older installs have it without
 * its executable bit.
 */
Singleton {
    id: root

    readonly property string updater: `${FileUtils.trimFileProtocol(Directories.config)}/hypr/hyprland/halcyon/update`

    property int count: 0
    readonly property bool available: root.count > 0
    property string error: ""
    readonly property bool applying: applyProc.running
    readonly property bool checking: checkProc.running

    // Called at start-up so the singleton exists from the start: Quickshell makes one only when it is first used.
    function load() {}

    function refresh() {
        stateProc.running = false;
        stateProc.running = true;
    }

    function check() {
        if (!checkProc.running && !applyProc.running)
            checkProc.running = true;
    }

    function apply() {
        if (applyProc.running)
            return;
        root.error = "";
        applyProc.running = true;
    }

    // Both state files in one read: the count on the first line ("0" when none), the last problem after it.
    Process {
        id: stateProc
        command: ["bash", "-c", "d=\"${XDG_STATE_HOME:-$HOME/.local/state}/halcyon\"; cat \"$d/update-available\" 2>/dev/null || echo 0; cat \"$d/update-error\" 2>/dev/null"]
        stdout: StdioCollector {
            onStreamFinished: {
                const lines = this.text.split("\n");
                const n = parseInt(lines[0]);
                root.count = isNaN(n) ? 0 : n;
                root.error = lines.slice(1).join(" ").trim();
            }
        }
    }

    Process {
        id: checkProc
        command: ["bash", root.updater, "check"]
        onExited: root.refresh()
    }

    Process {
        id: applyProc
        command: ["bash", root.updater, "apply"]
        onExited: root.refresh()
    }

    Timer {
        interval: 30000
        running: true
        repeat: true
        triggeredOnStart: true
        onTriggered: root.refresh()
    }

    // A check two minutes after the shell starts, then every three hours; the updater keeps it to one notification.
    Timer {
        interval: 120000
        running: true
        onTriggered: {
            root.check();
            interval = 3 * 60 * 60 * 1000;
            repeat = true;
            restart();
        }
    }

    IpcHandler {
        target: "halcyonUpdates"

        function check(): void {
            root.check();
        }
        function apply(): void {
            root.apply();
        }
        function status(): string {
            return root.available ? `${root.count} waiting` : (root.error !== "" ? `problem: ${root.error}` : "up to date");
        }
    }
}
