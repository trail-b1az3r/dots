pragma Singleton
pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Hyprland

/**
 * Screen brightness, as the Halcyon shell does it (its services/Brightness.qml, from caelestia-dots, GPLv3): a laptop's
 * own panel through brightnessctl, other monitors through DDC/CI (ddcutil), and below the backlight's lowest, the
 * picture itself made dimmer with hyprsunset's gamma.
 *
 * The slider runs 0..1 the way the Halcyon shell's does: the top 70% is the backlight, the bottom 30% is gamma (a sun
 * marks where one becomes the other). A screen with neither backlight nor DDC gets gamma over the whole slider.
 */
Singleton {
    id: root

    // Gamma: 100 is untouched; it goes no lower than this.
    readonly property int gammaFloor: 25
    property int gamma: 100
    readonly property real split: 0.3

    property var ddcMonitors: []
    readonly property list<QtObject> monitors: Quickshell.screens.map(screen => monitorComponent.createObject(root, { screen }))

    function forScreen(screen) {
        return root.monitors.find(m => m.screen === screen) ?? null;
    }
    function focused() {
        const name = Hyprland.focusedMonitor?.name;
        return root.monitors.find(m => m.screen?.name === name) ?? root.monitors[0] ?? null;
    }

    // The slider's value for a screen, and setting it.
    function value(monitor) {
        if (!monitor?.available)
            return (root.gamma - root.gammaFloor) / (100 - root.gammaFloor);
        if (root.gamma < 100)
            return (root.gamma - root.gammaFloor) / (100 - root.gammaFloor) * root.split;
        return root.split + monitor.brightness * (1 - root.split);
    }
    function setValue(monitor, v) {
        v = Math.max(0, Math.min(1, v));
        if (!monitor?.available) {
            root.setGamma(root.gammaFloor + v * (100 - root.gammaFloor));
            return;
        }
        if (v >= root.split) {
            monitor.set((v - root.split) / (1 - root.split));
            if (root.gamma !== 100)
                root.setGamma(100);
        } else {
            if (monitor.brightness !== 0)
                monitor.set(0);
            root.setGamma(root.gammaFloor + v / root.split * (100 - root.gammaFloor));
        }
    }
    function step(monitor, delta) {
        root.setValue(monitor, root.value(monitor) + delta);
    }

    function setGamma(value) {
        const g = Math.round(Math.max(root.gammaFloor, Math.min(100, value)));
        if (g === root.gamma)
            return;
        root.gamma = g;
        gammaTimer.restart();
    }
    // hyprsunset does the gamma (and Summit's night light): started when it is not running.
    Timer {
        id: gammaTimer
        interval: 60
        onTriggered: Quickshell.execDetached(["sh", "-c",
            "pidof hyprsunset >/dev/null || { hyprsunset >/dev/null 2>&1 & sleep 0.5; }; hyprctl hyprsunset gamma " + root.gamma])
    }

    Process {
        id: ddcDetect
        running: true
        command: ["sh", "-c", "command -v ddcutil >/dev/null && ddcutil detect --brief 2>/dev/null"]
        stdout: StdioCollector {
            onStreamFinished: {
                const found = [];
                for (const block of text.split("\n\n")) {
                    if (!block.startsWith("Display "))
                        continue;
                    const lines = block.split("\n").map(l => l.trim());
                    const connector = lines.find(l => l.startsWith("DRM connector:"));
                    const bus = lines.find(l => l.startsWith("I2C bus:"));
                    if (connector && bus)
                        found.push({ name: connector.split("-").slice(1).join("-"), bus: bus.split("/dev/i2c-")[1] });
                }
                root.ddcMonitors = found;
                for (const m of root.monitors)
                    m.initialize();
            }
        }
    }

    component Monitor: QtObject {
        id: monitor
        required property var screen
        // A laptop's own panel (eDP, LVDS, DSI) has the backlight; other monitors need DDC.
        readonly property bool internal: /^(eDP|LVDS|DSI)/.test(screen?.name ?? "")
        property string bus: ""
        readonly property bool ddc: bus !== ""
        property bool available: false
        property real brightness: 0.5
        property int max: 100

        function initialize() {
            const match = root.ddcMonitors.find(d => d.name === monitor.screen?.name);
            monitor.bus = match?.bus ?? "";
            if (monitor.ddc)
                read.command = ["ddcutil", "-b", monitor.bus, "getvcp", "10", "--brief"];
            else if (monitor.internal)
                read.command = ["sh", "-c", "command -v brightnessctl >/dev/null && echo \"x x x $(brightnessctl --class backlight g) $(brightnessctl --class backlight m)\""];
            else
                return;
            read.running = true;
        }
        function set(value) {
            monitor.brightness = Math.max(0, Math.min(1, value));
            write.restart();
        }

        readonly property Process read: Process {
            stdout: StdioCollector {
                onStreamFinished: {
                    const [, , , current, max] = text.trim().split(" ");
                    const c = parseInt(current), m = parseInt(max);
                    if (m > 0 && c >= 0) {
                        monitor.max = m;
                        monitor.brightness = c / m;
                        monitor.available = true;
                    }
                }
            }
        }
        // DDC monitors are slow, and odd with many changes in a row: one write once the value has settled.
        readonly property Timer write: Timer {
            interval: monitor.ddc ? 300 : 16
            onTriggered: {
                if (monitor.ddc)
                    Quickshell.execDetached(["ddcutil", "-b", monitor.bus, "setvcp", "10", String(Math.max(1, Math.round(monitor.brightness * monitor.max)))]);
                else
                    Quickshell.execDetached(["brightnessctl", "--class", "backlight", "s", Math.max(1, Math.round(monitor.brightness * 100)) + "%", "--quiet"]);
            }
        }
    }

    Component {
        id: monitorComponent
        Monitor {}
    }
}
