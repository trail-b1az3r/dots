pragma Singleton
pragma ComponentBehavior: Bound

import qs
import qs.modules.common
import qs.modules.common.functions
import QtQuick
import Quickshell
import Quickshell.Io

/**
 * The calendar's alarm: rings when an event with the alarm on starts (CalendarEvents), until it is stopped or
 * snoozed. First a smoke alarm, then, if nobody has stopped it after a minute, a tornado siren (Settings > General >
 * Calendar alarm changes both, or makes either silent). They play through the default output at its current volume.
 *
 * The sounds are made by scripts/alarm/alarm_sounds.py from sine waves, so nothing recorded by someone else is
 * shipped; they are written to the shell's state folder the first time.
 */
Singleton {
    id: root

    readonly property var settings: Config.options.calendar.alarm
    readonly property string soundDir: `${FileUtils.trimFileProtocol(Directories.state)}/user/alarm-sounds`
    readonly property string generator: FileUtils.trimFileProtocol(`${Directories.scriptPath}/alarm/alarm_sounds.py`)
    readonly property var builtIn: ["smoke", "tornado", "beep", "chime"]

    property bool ringing: false
    property var event: null      // {id, title, time} of what is ringing; id "" for a test
    property int stage: 0         // 1: the first sound, 2: the second
    property string playing: ""   // the file being played, "" when silent

    signal stopped
    signal snoozed(string id, int minutes)

    // Called at start-up, with CalendarEvents.load(), so the sounds are there before the first alarm.
    function load() {
        makeSounds.running = true;
    }

    // The file a sound setting names: a built-in one, a file of your own, or "" for silence.
    function soundFile(name) {
        const value = String(name ?? "").trim();
        if (value === "" || value === "silent" || value === "none")
            return "";
        if (root.builtIn.includes(value))
            return `${root.soundDir}/${value}.wav`;
        return value.startsWith("~/") ? `${FileUtils.trimFileProtocol(Directories.home)}/${value.slice(2)}` : value;
    }

    function describe(name) {
        const names = {
            "smoke": Translation.tr("Smoke alarm"),
            "tornado": Translation.tr("Tornado siren"),
            "beep": Translation.tr("Alarm clock"),
            "chime": Translation.tr("Chime"),
            "silent": Translation.tr("Silent"),
            "none": Translation.tr("Silent"),
            "": Translation.tr("Silent")
        };
        return names[name] ?? String(name).split("/").pop();
    }

    function ring(event) {
        root.event = event;
        root.ringing = true;
        root.stage = 1;
        root.play(root.settings.firstSound);
        escalate.restart();
        giveUp.restart();
        Quickshell.execDetached(["notify-send", "-a", Translation.tr("Calendar"), "-u", "critical", "-i", "alarm",
            event.title, event.time ? Translation.tr("Alarm, %1").arg(event.time) : Translation.tr("Alarm")]);
    }

    function play(name) {
        player.running = false;
        root.playing = root.soundFile(name);
        if (root.playing !== "") {
            player.command = ["bash", "-c", root.loopScript, "_", root.playing, root.generator, root.soundDir];
            player.running = true;
        }
    }

    function stop() {
        if (!root.ringing)
            return;
        escalate.stop();
        giveUp.stop();
        player.running = false;
        root.ringing = false;
        root.stage = 0;
        root.playing = "";
        root.stopped();
    }

    function snooze() {
        if (!root.ringing)
            return;
        const id = root.event?.id ?? "";
        const minutes = Math.max(1, root.settings.snoozeMinutes);
        root.stop();
        if (id !== "")
            root.snoozed(id, minutes);
    }

    // Plays the file over and over. A built-in sound that has gone missing is made again first. The players
    // are tried in turn: PipeWire's, PulseAudio's, ALSA's. Each plays at the output's current volume.
    readonly property string loopScript: 'f="$1"; '
        + 'if [ ! -f "$f" ] && [ "${f#$3/}" != "$f" ]; then python3 "$2" ensure "$3" >/dev/null; fi; '
        + 'p=""; for c in pw-play paplay aplay; do command -v "$c" >/dev/null && { p="$c"; break; }; done; '
        + '[ -n "$p" ] || { echo "no audio player (pw-play, paplay or aplay)" >&2; exit 1; }; '
        + 'while :; do "$p" "$f" || sleep 1; done'

    Process {
        id: player
    }

    Process {
        id: makeSounds
        command: ["python3", root.generator, "ensure", root.soundDir]
    }

    // No one stopped the first sound: the second takes over.
    Timer {
        id: escalate
        interval: Math.max(5, root.settings.escalateAfter) * 1000
        onTriggered: {
            const second = String(root.settings.secondSound ?? "");
            if (!root.ringing || second === "" || second === "none" || second === root.settings.firstSound)
                return;
            root.stage = 2;
            root.play(second);
        }
    }

    // Nobody is there: stop, and leave a notification saying so.
    Timer {
        id: giveUp
        interval: Math.max(1, root.settings.stopAfter) * 60000
        onTriggered: {
            const title = root.event?.title ?? "";
            root.stop();
            Quickshell.execDetached(["notify-send", "-a", Translation.tr("Calendar"), "-i", "alarm",
                Translation.tr("Missed alarm: %1").arg(title), Translation.tr("It rang for %1 minutes").arg(root.settings.stopAfter)]);
        }
    }

    IpcHandler {
        target: "alarm"

        function stop(): void {
            root.stop();
        }
        function snooze(): void {
            root.snooze();
        }
        // Rings now, as a real alarm would, without an event: Settings has a button for it.
        function test(): void {
            root.ring({ id: "", title: Translation.tr("Test alarm"), time: Qt.formatTime(new Date(), "hh:mm") });
        }
        function status(): string {
            return root.ringing ? `ringing, stage ${root.stage}, ${root.playing || "silent"}` : "quiet";
        }
    }
}
