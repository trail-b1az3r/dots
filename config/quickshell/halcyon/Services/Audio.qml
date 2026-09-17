pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Services.Pipewire
import qs.Config

/**
 * Output and input volume, straight from PipeWire.
 *
 * Reads and writes the node objects directly rather than shelling out to
 * wpctl: the values arrive as property changes, so a volume key pressed
 * anywhere updates the bar and the HUD without either of them polling.
 */
Singleton {
    id: root

    readonly property PwNode sink: Pipewire.defaultAudioSink
    readonly property PwNode source: Pipewire.defaultAudioSource

    readonly property bool ready: Pipewire.ready

    readonly property real volume: root.sink?.audio?.volume ?? 0
    readonly property bool muted: root.sink?.audio?.muted ?? false
    readonly property int volumePercent: Math.round(root.volume * 100)

    readonly property real inputVolume: root.source?.audio?.volume ?? 0
    readonly property bool inputMuted: root.source?.audio?.muted ?? false
    readonly property int inputPercent: Math.round(root.inputVolume * 100)

    readonly property string sinkName:
        root.sink?.nickname ?? root.sink?.description ?? root.sink?.name ?? "Output"
    readonly property string sourceName:
        root.source?.nickname ?? root.source?.description ?? root.source?.name ?? "Microphone"

    /** Nerd Font glyph for the current level, for the bar and the HUD. */
    readonly property string glyph: {
        if (root.muted) return "󰝟";
        if (root.volumePercent <= 0) return "󰕿";
        if (root.volumePercent < 34) return "󰕿";
        if (root.volumePercent < 67) return "󰖀";
        return "󰕾";
    }

    readonly property string inputGlyph: root.inputMuted ? "󰍭" : "󰍬"

    // Without a tracker the node's audio properties are never bound and
    // every read returns a default.
    PwObjectTracker {
        objects: [root.sink, root.source].filter(node => node !== null)
    }

    function setVolume(value: real): void {
        if (!root.sink?.audio)
            return;
        // 1.0 is the ceiling in the UI. Above it PipeWire will happily
        // amplify into clipping, which is not something a slider should
        // do by accident.
        root.sink.audio.volume = Math.max(0, Math.min(1, value));
    }

    function setMuted(value: bool): void {
        if (root.sink?.audio)
            root.sink.audio.muted = value;
    }

    function toggleMute(): void { root.setMuted(!root.muted); }

    function setInputVolume(value: real): void {
        if (root.source?.audio)
            root.source.audio.volume = Math.max(0, Math.min(1, value));
    }

    function toggleInputMute(): void {
        if (root.source?.audio)
            root.source.audio.muted = !root.inputMuted;
    }

    /** Every output the user could switch to. */
    readonly property var sinks: Pipewire.nodes.values.filter(
        node => node.isSink && node.audio && !node.isStream
    )

    /** Applications currently playing something. */
    readonly property var streams: Pipewire.nodes.values.filter(
        node => node.isStream && node.isSink && node.audio
    )

    function setDefaultSink(node: PwNode): void {
        Pipewire.preferredDefaultAudioSink = node;
    }
}
