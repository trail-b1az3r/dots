pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import qs.Config

/**
 * The assistant, as the UI sees it.
 *
 * Holds a long-lived connection to the daemon's socket so state changes
 * arrive as events rather than being polled, and a second, short-lived
 * connection per turn so a streaming reply can be rendered as it is
 * produced.
 *
 * When the daemon is not running, everything here reports `offline` and
 * the orb offers to start it. Nothing in the shell depends on the
 * assistant being present.
 */
Singleton {
    id: root

    /** offline | idle | listening | thinking | speaking */
    property string state: "offline"
    property string providerId: ""
    property string providerTitle: ""
    property string lastError: ""

    /** The turn being rendered: transcript, streamed reply, actions. */
    property string transcript: ""
    property string reply: ""
    property var actionsTaken: []
    property var pendingConfirmation: null

    /** [{ role, content }] — the conversation so far. */
    property var history: []

    readonly property bool enabled: Config.get("assistant.enabled", true)
    readonly property bool busy:
        root.state === "listening" || root.state === "thinking" || root.state === "speaking"
    readonly property bool online: root.state !== "offline"

    readonly property string glyph: {
        switch (root.state) {
        case "listening": return "󰍬";
        case "thinking": return "󰧑";
        case "speaking": return "󰔊";
        default: return "󰚩";
        }
    }

    readonly property string statusText: {
        switch (root.state) {
        case "listening": return "Listening…";
        case "thinking": return "Thinking…";
        case "speaking": return "Speaking";
        case "idle": return root.providerTitle.length > 0 ? root.providerTitle : "Ready";
        default: return "Not running";
        }
    }

    /** A crude level for the waveform while listening. */
    property real level: 0

    signal turnFinished(string answer)

    // ── Commands ───────────────────────────────────────────────────────

    function listen(): void {
        root.beginTurn();
        turn.command = Paths.command(["assistant", "listen"]);
        turn.running = true;
    }

    function ask(prompt: string): void {
        if (!prompt || prompt.trim().length === 0)
            return;
        root.beginTurn();
        root.transcript = prompt;
        turn.command = Paths.command(["assistant", "ask", prompt]);
        turn.running = true;
    }

    function cancel(): void {
        Quickshell.execDetached(Paths.command(["assistant", "cancel"]));
        root.state = "idle";
    }

    function confirm(accept: bool): void {
        root.pendingConfirmation = null;
        Quickshell.execDetached(
            Paths.command(["assistant", "confirm", accept ? "yes" : "no"])
        );
    }

    function start(): void {
        Quickshell.execDetached(Paths.command(["assistant", "start"]));
        reconnect.restart();
    }

    function clearConversation(): void {
        root.history = [];
        root.transcript = "";
        root.reply = "";
        root.actionsTaken = [];
        Quickshell.execDetached(Paths.command(["assistant", "clear"]));
    }

    function beginTurn(): void {
        root.transcript = "";
        root.reply = "";
        root.actionsTaken = [];
        root.lastError = "";
        root.pendingConfirmation = null;
    }

    // ── The turn ───────────────────────────────────────────────────────

    Process {
        id: turn
        // `assistant ask`/`listen` print the answer on stdout when not
        // attached to a terminal, and the daemon streams events over the
        // socket that the subscription below is already watching.
        stdout: StdioCollector {
            onStreamFinished: {
                const answer = this.text.trim();
                if (answer.length > 0) {
                    root.reply = answer;
                    root.history = root.history.concat([
                        { role: "user", content: root.transcript },
                        { role: "assistant", content: answer }
                    ]);
                }
                root.turnFinished(answer);
            }
        }
    }

    // ── Live state ─────────────────────────────────────────────────────
    //
    // A subscription rather than a poll: the daemon pushes state changes,
    // deltas and actions down this socket for as long as it is open.

    Socket {
        id: events
        path: Quickshell.env("XDG_RUNTIME_DIR")
            ? Quickshell.env("XDG_RUNTIME_DIR") + "/halcyon-assistant.sock"
            : "/tmp/halcyon-assistant.sock"

        connected: root.enabled

        onConnectionStateChanged: {
            if (this.connected) {
                this.write('{"op":"subscribe"}\n');
                this.flush();
                root.state = "idle";
                reconnect.stop();
            } else {
                root.state = "offline";
                if (root.enabled)
                    reconnect.restart();
            }
        }

        onError: {
            root.state = "offline";
            if (root.enabled)
                reconnect.restart();
        }

        parser: SplitParser {
            onRead: line => root.handleEvent(line)
        }
    }

    function handleEvent(line: string): void {
        let event;
        try {
            event = JSON.parse(line);
        } catch (error) {
            return;
        }

        switch (event.event) {
        case "state":
            root.state = event.state ?? root.state;
            break;
        case "transcript":
            root.transcript = event.text ?? "";
            break;
        case "delta":
            root.reply += event.text ?? "";
            break;
        case "action":
            root.actionsTaken = root.actionsTaken.concat([{
                title: event.text ?? "",
                action: (event.data ?? ({})).action ?? "",
                source: (event.data ?? ({})).source ?? ""
            }]);
            break;
        case "confirm":
            root.pendingConfirmation = {
                text: event.text ?? "",
                action: (event.data ?? ({})).action ?? "",
                params: (event.data ?? ({})).params ?? ({})
            };
            break;
        case "error":
            root.lastError = event.text ?? "";
            root.state = "idle";
            break;
        case "cleared":
            root.history = [];
            break;
        }
    }

    /**
     * Reconnect with a backoff.
     *
     * The daemon is often simply not running, and a socket retried every
     * 200 ms forever is a busy loop with extra steps.
     */
    property int retryDelay: 2000

    Timer {
        id: reconnect
        interval: root.retryDelay
        repeat: false
        onTriggered: {
            if (!root.enabled)
                return;
            events.connected = true;
            root.retryDelay = Math.min(root.retryDelay * 2, 60000);
        }
    }

    onStateChanged: {
        if (root.state !== "offline")
            root.retryDelay = 2000;
    }

    // A gentle idle pulse for the orb while listening, in place of real
    // level metering — PwNodePeakMonitor on the microphone would give a
    // true level, but keeping a capture stream open on the default source
    // just to animate an orb is not a trade worth making.
    Timer {
        running: root.state === "listening" && Theme.animationsEnabled
        interval: 90
        repeat: true
        onTriggered: root.level = 0.35 + Math.random() * 0.5
    }

    onBusyChanged: {
        if (!root.busy)
            root.level = 0;
    }
}
