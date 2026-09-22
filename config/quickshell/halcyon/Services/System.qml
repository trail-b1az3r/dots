pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import qs.Config

/**
 * CPU, memory, temperature, disk and network throughput.
 *
 * Reads `halcyon status system`, which reads /proc and /sys. Nothing
 * here shells out to a monitoring tool, and nothing is fabricated: a
 * machine with no temperature sensor reports `hasTemperature: false`
 * and the module that shows it hides itself rather than printing a
 * plausible number.
 *
 * Polling follows the power policy — the interval comes from settings
 * and doubles on battery — and stops entirely when nothing is watching.
 * `subscribe()`/`unsubscribe()` are reference-counted, so a bar with no
 * system modules costs nothing.
 */
Singleton {
    id: root

    property var snapshot: ({})
    readonly property bool loaded: root.snapshot.cpuCount !== undefined

    // CPU is a rate and needs two samples; until then it is unknown
    // rather than zero, and a module showing 0% when it means "not yet"
    // is a lie a progress bar tells convincingly.
    readonly property bool hasCpu: root.snapshot.cpuPercent !== undefined
        && root.snapshot.cpuPercent !== null
    readonly property real cpuPercent: root.hasCpu ? root.snapshot.cpuPercent : 0
    readonly property int cpuCount: root.snapshot.cpuCount ?? 1
    readonly property var loadAverage: root.snapshot.loadAverage ?? []

    readonly property var memory: root.snapshot.memory ?? ({})
    readonly property real memoryPercent: root.memory.percent ?? 0
    readonly property int memoryTotalKb: root.memory.total_kb ?? 0
    readonly property int memoryUsedKb: root.memory.used_kb ?? 0
    readonly property real swapPercent: root.memory.swap_percent ?? 0
    readonly property bool hasSwap: (root.memory.swap_total_kb ?? 0) > 0

    readonly property bool hasTemperature: root.snapshot.temperatureC !== undefined
        && root.snapshot.temperatureC !== null
    readonly property real temperature: root.hasTemperature
        ? root.snapshot.temperatureC : 0

    readonly property var disk: root.snapshot.disk ?? ({})
    readonly property real diskPercent: root.disk.percent ?? 0
    readonly property real diskFreeBytes: root.disk.free_bytes ?? 0

    readonly property bool hasNetworkRate: root.snapshot.network !== undefined
        && root.snapshot.network !== null
    readonly property real downBytesPerSecond: root.hasNetworkRate
        ? (root.snapshot.network.downBytesPerSecond ?? 0) : 0
    readonly property real upBytesPerSecond: root.hasNetworkRate
        ? (root.snapshot.network.upBytesPerSecond ?? 0) : 0

    // ── Subscription ───────────────────────────────────────────────────

    property int watchers: 0

    function subscribe(): void {
        root.watchers += 1;
        if (root.watchers === 1) {
            root.refresh();
        }
    }

    function unsubscribe(): void {
        root.watchers = Math.max(0, root.watchers - 1);
    }

    readonly property int interval: {
        const base = Config.get("power.refreshIntervals.acSeconds", 5);
        const onBattery = Config.get("power.refreshIntervals.batterySeconds", 15);
        return Math.max(1, Power.onBattery ? onBattery : base) * 1000;
    }

    function refresh(): void {
        if (root.watchers <= 0) {
            return;
        }
        reader.running = false;
        reader.running = true;
    }

    Timer {
        interval: root.interval
        repeat: true
        running: root.watchers > 0
        onTriggered: root.refresh()
    }

    Process {
        id: reader

        command: Paths.command(["status", "system"])

        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    root.snapshot = JSON.parse(this.text);
                } catch (error) {
                    // A malformed reading is not worth replacing a good
                    // one with; the next tick will try again.
                }
            }
        }
    }

    // ── Formatting ─────────────────────────────────────────────────────

    function humanBytes(value: real): string {
        let amount = Math.abs(value);
        const units = ["B", "kB", "MB", "GB", "TB"];
        let index = 0;
        while (amount >= 1024 && index < units.length - 1) {
            amount /= 1024;
            index += 1;
        }
        if (index === 0) {
            return Math.round(amount) + " B";
        }
        return (amount < 10 ? amount.toFixed(1) : Math.round(amount))
            + " " + units[index];
    }

    function humanRate(bytesPerSecond: real): string {
        return root.humanBytes(bytesPerSecond) + "/s";
    }
}
