pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Services.Mpris
import qs.Config

/**
 * Now Playing, over MPRIS.
 *
 * Picks one player to be "the" player so the bar and the Control Center
 * agree: the one that is playing, else the last one that was, else the
 * first that exists. A bar that switches between two paused players every
 * few seconds is worse than one that picks wrong.
 */
Singleton {
    id: root

    property MprisPlayer active: null

    readonly property var players: Mpris.players.values
    readonly property bool hasPlayer: root.active !== null

    readonly property bool playing:
        root.active?.playbackState === MprisPlaybackState.Playing
    readonly property string title: root.active?.trackTitle ?? ""
    readonly property string artist: root.active?.trackArtist ?? ""
    readonly property string album: root.active?.trackAlbum ?? ""
    readonly property string artUrl: root.active?.trackArtUrl ?? ""
    readonly property string identity: root.active?.identity ?? ""

    readonly property real length: root.active?.length ?? 0
    readonly property bool canSeek: root.active?.canSeek ?? false
    readonly property bool canGoNext: root.active?.canGoNext ?? false
    readonly property bool canGoPrevious: root.active?.canGoPrevious ?? false

    property real position: 0

    readonly property string statusGlyph: root.playing ? "󰏤" : "󰐊"

    function choose(): void {
        const all = Mpris.players.values;
        if (all.length === 0) {
            root.active = null;
            return;
        }
        // Prefer whatever is actually making sound.
        for (const player of all) {
            if (player.playbackState === MprisPlaybackState.Playing) {
                root.active = player;
                return;
            }
        }
        // Then keep the current one if it is still around, so pausing does
        // not hand the bar to a different application.
        if (root.active && all.indexOf(root.active) >= 0)
            return;
        root.active = all[0];
    }

    function playPause(): void { root.active?.togglePlaying(); }
    function next(): void { root.active?.next(); }
    function previous(): void { root.active?.previous(); }

    function seek(fraction: real): void {
        if (!root.active || !root.canSeek || root.length <= 0)
            return;
        root.active.position = Math.max(0, Math.min(1, fraction)) * root.length;
    }

    function raise(): void { root.active?.raise(); }

    Connections {
        target: Mpris.players
        function onValuesChanged(): void { root.choose(); }
    }

    Connections {
        target: root.active
        enabled: root.active !== null
        function onPlaybackStateChanged(): void { root.choose(); }
    }

    /**
     * Position ticks locally while playing rather than being polled.
     *
     * MPRIS position is expensive to read (a D-Bus round trip per
     * request) and players do not signal it. One second of drift is
     * invisible on a progress bar; a D-Bus call every frame is not.
     */
    Timer {
        running: root.playing && Overlays.current !== ""
        interval: 1000
        repeat: true
        onTriggered: {
            if (root.active)
                root.position = root.active.position;
        }
    }

    Component.onCompleted: root.choose()
}
