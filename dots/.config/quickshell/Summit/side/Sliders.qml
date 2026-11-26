pragma ComponentBehavior: Bound

import QtQuick
import Quickshell.Services.Pipewire
import qs.common
import qs.services

// The side menu's sliders, as the Halcyon shell's quick sliders: brightness (backlight, then dimming below the sun),
// the volume and the microphone.
Rectangle {
    id: root
    required property var screen
    readonly property var monitor: Brightness.forScreen(root.screen)
    readonly property PwNode sink: Pipewire.defaultAudioSink
    readonly property PwNode source: Pipewire.defaultAudioSource
    PwObjectTracker { objects: [root.sink, root.source] }

    implicitHeight: col.implicitHeight + 24
    radius: Theme.radius + 2
    color: Theme.alpha(Theme.text, 0.06)

    Column {
        id: col
        x: 12
        y: 12
        width: parent.width - 24
        spacing: 10

        Slider {
            width: parent.width
            implicitHeight: 34
            icon: "light_mode"
            markIcon: root.monitor?.available ? "wb_twilight" : ""
            markAt: Brightness.split
            value: Brightness.value(root.monitor)
            valueText: root.monitor?.available && Brightness.gamma === 100 ? Math.round((root.monitor?.brightness ?? 0) * 100) + "%"
                : "Dimmed " + Brightness.gamma + "%"
            onMoved: v => Brightness.setValue(root.monitor, v)
        }
        Slider {
            width: parent.width
            implicitHeight: 34
            visible: root.sink?.audio !== undefined && root.sink !== null
            icon: (root.sink?.audio?.muted ?? false) ? "volume_off" : "volume_up"
            value: Math.min(1, root.sink?.audio?.volume ?? 0)
            onMoved: v => { if (root.sink?.audio) { root.sink.audio.volume = v; root.sink.audio.muted = false; } }
        }
        Slider {
            width: parent.width
            implicitHeight: 34
            visible: root.source?.audio !== undefined && root.source !== null
            icon: (root.source?.audio?.muted ?? false) ? "mic_off" : "mic"
            value: Math.min(1, root.source?.audio?.volume ?? 0)
            onMoved: v => { if (root.source?.audio) { root.source.audio.volume = v; root.source.audio.muted = false; } }
        }
    }
}
