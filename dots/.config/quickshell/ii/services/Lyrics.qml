pragma Singleton
pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Services.Mpris
import qs.services
import "../modules/ii/background/widgets/lyrics/LyricsParse.js" as Parse

/**
 * Synced lyrics for what is playing, from LRCLIB (lrclib.net: free, no account, no key). It only asks the network
 * while a lyrics widget is on a desktop, once per song, and remembers the last few. The artist, title and length of
 * the song are sent to LRCLIB, and nothing else.
 */
Singleton {
    id: root

    /** How many lyrics widgets are showing. */
    property int users: 0

    readonly property var player: MprisController.activePlayer
    readonly property var track: MprisController.activeTrack
    readonly property string artist: track?.artist ?? ""
    readonly property string title: track?.title ?? ""
    readonly property real length: player?.length ?? 0
    readonly property string key: (artist + "\n" + title).trim() === "" ? "" : artist + "\n" + title

    /** "idle" (nothing asked), "loading", "synced", "plain" (words but no timing), "none". */
    property string state: "idle"
    property var lines: []
    property int index: -1
    /** Seconds the words are shifted by: positive shows lines earlier. */
    property real offset: 0.25

    property var cache: ({})

    onKeyChanged: {
        index = -1;
        lines = [];
        lookup.restart();
    }
    onUsersChanged: lookup.restart()

    Timer {
        id: lookup
        interval: 500   // a skipped song is not looked up
        onTriggered: root.fetch()
    }

    function fetch() {
        if (users <= 0 || key === "") {
            state = "idle";
            return;
        }
        const cached = cache[key];
        if (cached) {
            apply(cached);
            return;
        }
        state = "loading";
        wanted = key;
        search.command = ["bash", "-c", root.script, "_", artist, title, String(Math.round(length))];
        search.running = false;
        search.running = true;
    }

    property string wanted: ""
    function apply(result) {
        lines = result.lines;
        state = result.state;
        index = Parse.indexAt(lines, (player?.position ?? 0) + offset);
    }

    // LRCLIB asks for a User-Agent that names the app. /get wants the length within two seconds; when it has nothing,
    // the search answers with a list. QML reads what comes back, so nothing but curl is needed.
    readonly property string script:
        'ua="halcyon-dots (https://github.com/trail-b1az3r/dots)"; '
        + 'curl -fsS -m 10 -A "$ua" -G https://lrclib.net/api/get --data-urlencode "artist_name=$1" '
        + '--data-urlencode "track_name=$2" ${3:+--data-urlencode "duration=$3"} '
        + '|| curl -fsS -m 10 -A "$ua" -G https://lrclib.net/api/search --data-urlencode "artist_name=$1" '
        + '--data-urlencode "track_name=$2"'

    Process {
        id: search
        stdout: StdioCollector {
            onStreamFinished: {
                const result = Parse.interpret(this.text);
                if (root.wanted !== root.key)
                    return; // the song changed while the answer was coming
                const keep = root.cache;
                keep[root.key] = result;
                const keys = Object.keys(keep);
                if (keys.length > 20)
                    delete keep[keys[0]];
                root.apply(result);
            }
        }
    }

    // The position is not pushed while a song plays.
    Timer {
        interval: 250
        repeat: true
        running: root.users > 0 && root.state === "synced" && root.player?.playbackState === MprisPlaybackState.Playing
        onTriggered: {
            root.player?.positionChanged();
            const next = Parse.indexAt(root.lines, (root.player?.position ?? 0) + root.offset);
            if (next !== root.index)
                root.index = next;
        }
    }
    // Seeking while paused.
    Connections {
        target: root.player
        function onPositionChanged() {
            if (root.state === "synced")
                root.index = Parse.indexAt(root.lines, (root.player?.position ?? 0) + root.offset);
        }
    }
}
