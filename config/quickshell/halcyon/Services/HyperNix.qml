pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import qs.Config

/**
 * The HyperNix integration.
 *
 * A thin, entirely optional adapter: everything it shows comes from
 * `halcyon hypernix status`, which probes the real CLI. When HyperNix is
 * not installed — or the integration is switched off — every consumer
 * sees `available: false` and simply does not draw.
 *
 * Polled slowly and only while something is displaying it, because
 * HyperNix's device probe spins up its Python runtime.
 */
Singleton {
    id: root

    property var info: ({})
    property bool refreshing: false

    readonly property bool enabled: Config.get("hypernix.enabled", true)
    readonly property bool installed: root.info.installed ?? false
    readonly property bool available: root.enabled && root.installed
    readonly property string version: root.info.version ?? ""
    readonly property string summary: root.info.summary ?? ""
    readonly property var devices: root.info.devices ?? []
    readonly property string autoDevice: root.info.autoDevice ?? ""

    readonly property int pollSeconds: Math.max(30, Config.get("hypernix.pollSeconds", 60))

    /** Set by any surface currently showing HyperNix state. */
    property int watchers: 0

    function refresh(): void {
        if (!root.enabled || root.refreshing)
            return;
        root.refreshing = true;
        reader.running = true;
    }

    function launch(): void {
        Quickshell.execDetached(Paths.command(["hypernix", "launch"]));
    }

    Process {
        id: reader
        command: Paths.command(["hypernix", "status"])
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    root.info = JSON.parse(this.text);
                } catch (error) {
                    root.info = ({ enabled: root.enabled, installed: false });
                }
                root.refreshing = false;
            }
        }
        onExited: root.refreshing = false
    }

    Timer {
        running: root.enabled && root.watchers > 0
        interval: root.pollSeconds * 1000
        repeat: true
        triggeredOnStart: true
        onTriggered: root.refresh()
    }

    Component.onCompleted: {
        if (root.enabled)
            root.refresh();
    }
}
