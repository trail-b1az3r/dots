pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Services.Pipewire
import Quickshell.Services.UPower
import qs.common
import qs.services

// Network, sound and battery, as plain symbols with the number where it helps; the power button at the end.
Row {
    id: root
    spacing: 2

    // Network: the active connection's kind and Wi-Fi strength (nmcli; nmxcli answers the same on Frontline).
    property string netKind: "none"
    property int wifiSignal: 0
    property string netName: ""
    Process {
        id: net
        command: ["sh", "-c", "c=nmcli; command -v nmxcli >/dev/null && nmxcli -t -f RUNNING general 2>/dev/null | grep -qx running && c=nmxcli; "
            + "$c -t -f TYPE,STATE,CONNECTION device 2>/dev/null | awk -F: '$2==\"connected\"{print $1\":\"$3; exit}'; "
            + "$c -t -f ACTIVE,SIGNAL dev wifi 2>/dev/null | awk -F: '$1==\"yes\"{print \"signal:\"$2; exit}'"]
        stdout: StdioCollector {
            onStreamFinished: {
                let kind = "none", name = "", signal = 0;
                for (const line of text.trim().split("\n")) {
                    const [a, b] = line.split(":");
                    if (a === "signal") signal = parseInt(b) || 0;
                    else if (a) { kind = a; name = b ?? ""; }
                }
                root.netKind = kind; root.netName = name; root.wifiSignal = signal;
            }
        }
    }
    Timer {
        interval: 8000
        running: true
        repeat: true
        triggeredOnStart: true
        onTriggered: net.running = true
    }

    BarButton {
        icon: root.netKind === "wifi" ? (root.wifiSignal > 66 ? "wifi" : root.wifiSignal > 33 ? "wifi_2_bar" : "wifi_1_bar")
            : root.netKind === "ethernet" ? "lan" : "wifi_off"
        tint: root.netKind === "none" ? Theme.muted : Theme.text
        onClicked: Actions.run("nm-connection-editor || nmtui-connect")
    }

    // Sound: the default output's volume; scroll to change it, click to mute.
    readonly property PwNode sink: Pipewire.defaultAudioSink
    PwObjectTracker { objects: [root.sink] }
    readonly property real volume: root.sink?.audio?.volume ?? 0
    readonly property bool muted: root.sink?.audio?.muted ?? false
    BarButton {
        visible: root.sink !== null
        icon: root.muted ? "volume_off" : root.volume > 0.6 ? "volume_up" : root.volume > 0.2 ? "volume_down" : "volume_mute"
        label: root.muted ? "" : Math.round(root.volume * 100) + "%"
        onClicked: if (root.sink?.audio) root.sink.audio.muted = !root.sink.audio.muted
        onRightClicked: Actions.run("pavucontrol-qt || pavucontrol")
        onScrolled: delta => {
            if (root.sink?.audio)
                root.sink.audio.volume = Math.max(0, Math.min(1.5, root.sink.audio.volume + (delta > 0 ? 0.05 : -0.05)));
        }
    }

    // Battery, on a laptop.
    readonly property var battery: UPower.displayDevice
    readonly property bool hasBattery: battery?.isLaptopBattery ?? false
    readonly property bool charging: battery?.state === UPowerDeviceState.Charging
    readonly property real level: battery?.percentage ?? 1
    BarButton {
        visible: root.hasBattery
        icon: root.charging ? "battery_charging_full" : root.level > 0.8 ? "battery_full" : root.level > 0.5 ? "battery_5_bar"
            : root.level > 0.2 ? "battery_3_bar" : "battery_1_bar"
        tint: !root.charging && root.level <= 0.15 ? "#FF8A80" : Theme.text
        label: Math.round(root.level * 100) + "%"
    }

    BarButton {
        icon: "power_settings_new"
        onClicked: Actions.power()
    }
}
