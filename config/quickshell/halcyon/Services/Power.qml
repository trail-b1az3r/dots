pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Services.UPower
import qs.Config

/**
 * Battery, charging state and the power profile.
 *
 * UPower supplies the battery over D-Bus, which is event-driven and
 * costs nothing while idle. The profile goes through the CLI so that the
 * shell, the bar and the keybind all end up in the same place — including
 * the part where it refuses to drive two power daemons at once.
 */
Singleton {
    id: root

    readonly property UPowerDevice device: UPower.displayDevice
    readonly property bool hasBattery:
        root.device !== null && root.device.isLaptopBattery && root.device.isPresent

    readonly property real percentage: root.device?.percentage ?? 100
    readonly property int percent: Math.round(root.percentage)
    readonly property bool onBattery: UPower.onBattery
    readonly property bool charging:
        root.device?.state === UPowerDeviceState.Charging
    readonly property bool full: root.device?.state === UPowerDeviceState.FullyCharged

    readonly property real timeToEmpty: root.device?.timeToEmpty ?? 0
    readonly property real timeToFull: root.device?.timeToFull ?? 0
    readonly property real changeRate: root.device?.changeRate ?? 0
    readonly property real health: root.device?.healthPercentage ?? 0
    readonly property bool healthKnown: root.device?.healthSupported ?? false

    readonly property bool low: root.hasBattery && root.onBattery && root.percent <= 20
    readonly property bool critical: root.hasBattery && root.onBattery && root.percent <= 10

    readonly property string glyph: {
        if (!root.hasBattery) return "󰚥";
        if (root.charging) return "󰂄";
        const steps = ["󰂎", "󰁺", "󰁻", "󰁼", "󰁽", "󰁾", "󰁿", "󰂀", "󰂁", "󰂂", "󰁹"];
        return steps[Math.max(0, Math.min(10, Math.round(root.percent / 10)))];
    }

    /** A human sentence, not a raw number of seconds. */
    readonly property string remaining: {
        const seconds = root.charging ? root.timeToFull : root.timeToEmpty;
        if (!root.hasBattery || seconds <= 0)
            return root.charging ? "Charging" : (root.onBattery ? "" : "Plugged in");
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const duration = hours > 0 ? hours + " hr " + minutes + " min" : minutes + " min";
        return root.charging ? duration + " until full" : duration + " remaining";
    }

    // ── Profile ────────────────────────────────────────────────────────

    readonly property bool profilesAvailable: PowerProfiles.hasPerformanceProfile
        || PowerProfiles.profile !== undefined

    readonly property string profile: {
        switch (PowerProfiles.profile) {
        case PowerProfile.Performance: return "performance";
        case PowerProfile.PowerSaver: return "battery-saver";
        default: return "balanced";
        }
    }

    readonly property var profiles: ["performance", "balanced", "battery-saver"]

    function profileTitle(name: string): string {
        switch (name) {
        case "performance": return "Performance";
        case "battery-saver": return "Battery Saver";
        default: return "Balanced";
        }
    }

    function profileGlyph(name: string): string {
        switch (name) {
        case "performance": return "󰓅";
        case "battery-saver": return "󰌪";
        default: return "󰾅";
        }
    }

    function setProfile(name: string): void {
        Quickshell.execDetached(Paths.command(["power", "profile", name]));
    }

    function cycleProfile(): void {
        Quickshell.execDetached(Paths.command(["power", "cycle"]));
    }

    /** The adaptive policy, as `halcyon power watch` last wrote it. */
    property var policy: ({})

    FileView {
        path: Paths.state + "/power.json"
        watchChanges: true
        printErrors: false
        onFileChanged: this.reload()
        onLoaded: {
            try {
                root.policy = JSON.parse(this.text()).policy ?? ({});
            } catch (error) {
                root.policy = ({});
            }
        }
    }
}
