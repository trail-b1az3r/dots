pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Bluetooth
import Quickshell.Services.Pipewire
import Quickshell.Services.UPower
import qs.common
import qs.services

// The side menu's quick toggles, the Halcyon shell's quick panel's in Summit's shape, four across: Wi-Fi, Bluetooth,
// sound, the microphone, do not disturb ("Silent"), night light, keep awake, game mode, the power profile, the super
// battery saver, the colour picker and a screenshot. Wi-Fi, Bluetooth and sound open a page of their own from their arrows.
Grid {
    id: root
    columns: 4
    columnSpacing: 6
    rowSpacing: 6
    signal pageRequested(string page)
    signal closeRequested

    readonly property real tileWidth: (width - columnSpacing * 3) / 4
    readonly property PwNode sink: Pipewire.defaultAudioSink
    readonly property PwNode source: Pipewire.defaultAudioSource
    PwObjectTracker { objects: [root.sink, root.source] }
    readonly property var adapter: Bluetooth.defaultAdapter
    readonly property var connectedDevice: (adapter?.devices?.values ?? []).find(d => d.connected) ?? null

    // The battery saver is on while its state file exists (halcyon_saver.py).
    property bool saverOn: false
    FileView {
        path: SummitState.stateDir + "/saver.json"
        watchChanges: true
        printErrors: false
        onFileChanged: reload()
        onLoaded: root.saverOn = true
        onLoadFailed: root.saverOn = false
    }

    function nodeName(node) {
        return node?.nickname || node?.description || node?.name || "";
    }

    Tile {
        width: root.tileWidth
        icon: !Network.enabled ? "wifi_off" : Network.signal > 66 ? "wifi" : Network.signal > 33 ? "wifi_2_bar" : "wifi_1_bar"
        title: Network.enabled && Network.ssid !== "" ? Network.ssid : "Wi-Fi"
        on: Network.enabled
        hasPage: true
        onClicked: Network.setEnabled(!Network.enabled)
        onPageRequested: root.pageRequested("wifi")
    }
    Tile {
        width: root.tileWidth
        icon: root.adapter?.enabled ? (root.connectedDevice ? "bluetooth_connected" : "bluetooth") : "bluetooth_disabled"
        title: root.connectedDevice?.name ?? "Bluetooth"
        on: root.adapter?.enabled ?? false
        hasPage: root.adapter !== null
        onClicked: if (root.adapter) root.adapter.enabled = !root.adapter.enabled
        onPageRequested: root.pageRequested("bluetooth")
    }
    Tile {
        width: root.tileWidth
        icon: (root.sink?.audio?.muted ?? false) ? "volume_off" : "volume_up"
        title: "Sound"
        on: !(root.sink?.audio?.muted ?? true)
        hasPage: true
        onClicked: if (root.sink?.audio) root.sink.audio.muted = !root.sink.audio.muted
        onPageRequested: root.pageRequested("sound")
    }
    Tile {
        width: root.tileWidth
        icon: (root.source?.audio?.muted ?? false) ? "mic_off" : "mic"
        title: "Mic"
        on: !(root.source?.audio?.muted ?? true)
        hasPage: true
        onClicked: if (root.source?.audio) root.source.audio.muted = !root.source.audio.muted
        onPageRequested: root.pageRequested("sound")
    }
    Tile {
        width: root.tileWidth
        icon: Prefs.doNotDisturb ? "do_not_disturb_on" : "notifications"
        title: "Silent"
        on: Prefs.doNotDisturb
        onClicked: Prefs.set("notifications.do_not_disturb", !Prefs.doNotDisturb)
    }
    Tile {
        width: root.tileWidth
        icon: "nightlight"
        title: "Night light"
        on: SummitState.nightLight
        onClicked: SummitState.nightLight = !SummitState.nightLight
    }
    Tile {
        width: root.tileWidth
        icon: "coffee"
        title: "Awake"
        on: SummitState.keepAwake
        onClicked: SummitState.keepAwake = !SummitState.keepAwake
    }
    Tile {
        width: root.tileWidth
        icon: "sports_esports"
        title: "Game"
        on: SummitState.gameMode
        onClicked: SummitState.setGameMode(!SummitState.gameMode)
    }
    Tile {
        width: root.tileWidth
        readonly property var profiles: [PowerProfile.PowerSaver, PowerProfile.Balanced].concat(PowerProfiles.hasPerformanceProfile ? [PowerProfile.Performance] : [])
        icon: PowerProfiles.profile === PowerProfile.PowerSaver ? "eco" : PowerProfiles.profile === PowerProfile.Performance ? "speed" : "balance"
        title: PowerProfiles.profile === PowerProfile.PowerSaver ? "Saver" : PowerProfiles.profile === PowerProfile.Performance ? "Fast" : "Balanced"
        on: PowerProfiles.profile !== PowerProfile.Balanced
        onClicked: PowerProfiles.profile = profiles[(profiles.indexOf(PowerProfiles.profile) + 1) % profiles.length]
    }
    Tile {
        width: root.tileWidth
        icon: "battery_saver"
        title: "Super saver"
        on: root.saverOn
        onClicked: {
            root.saverOn = !root.saverOn;   // at once; the state file confirms it
            Quickshell.execDetached([Actions.halcyon + "/halcyon_saver.py", "toggle"]);
        }
    }
    Tile {
        width: root.tileWidth
        icon: "colorize"
        title: "Colour"
        onClicked: {
            root.closeRequested();
            Actions.run("sleep 0.3; hyprpicker -a");
        }
    }
    Tile {
        width: root.tileWidth
        icon: "screenshot_region"
        title: "Screenshot"
        onClicked: {
            root.closeRequested();
            Actions.run("sleep 0.3; hyprshot --freeze --clipboard-only --mode region --silent");
        }
    }
}
