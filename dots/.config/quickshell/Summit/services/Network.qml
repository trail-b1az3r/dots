pragma Singleton
pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Io

/**
 * Wi-Fi for the side menu: on or off, the network in use, the networks in range, and connecting to one. Through
 * NetworkManager's nmcli, or nmxcli (the same commands) when Frontline's nmx is running. Asked again every few seconds
 * only while the side menu is open (`watching`).
 */
Singleton {
    id: root

    property bool watching: false
    property bool enabled: true
    property string ssid: ""
    property int signal: 0
    property var networks: []        // [{ssid, signal, secure, active, known}]
    property bool scanning: false
    property string connecting: ""
    property string error: ""

    readonly property string cli: "c=nmcli; command -v nmxcli >/dev/null && nmxcli -t -f RUNNING general 2>/dev/null | grep -qx running && c=nmxcli; "

    // nmcli -t's fields: split at the colons that are not escaped (a backslash before a colon keeps it inside the field).
    function fields(line) {
        const out = [];
        let field = "";
        for (let i = 0; i < line.length; i++) {
            if (line[i] === "\\" && i + 1 < line.length) {
                field += line[i] + line[i + 1];
                i++;
            } else if (line[i] === ":") {
                out.push(field);
                field = "";
            } else {
                field += line[i];
            }
        }
        out.push(field);
        return out;
    }

    function refresh() {
        state.running = true;
    }
    function setEnabled(on) {
        root.enabled = on;
        Quickshell.execDetached(["sh", "-c", root.cli + "$c radio wifi " + (on ? "on" : "off")]);
        refreshSoon.restart();
    }
    function scan() {
        root.scanning = true;
        list.running = true;
    }
    function connect(ssid, password) {
        root.connecting = ssid;
        root.error = "";
        join.command = ["sh", "-c", root.cli + (password
            ? "$c dev wifi connect \"$1\" password \"$2\""
            : "$c connection up id \"$1\" 2>/dev/null || $c dev wifi connect \"$1\""), "sh", ssid, password ?? ""];
        join.running = true;
    }
    function disconnect() {
        Quickshell.execDetached(["sh", "-c", root.cli + "d=$($c -t -f TYPE,DEVICE device | awk -F: '$1==\"wifi\"{print $2; exit}'); [ -n \"$d\" ] && $c device disconnect \"$d\""]);
        refreshSoon.restart();
    }

    Timer {
        interval: 6000
        running: root.watching
        repeat: true
        triggeredOnStart: true
        onTriggered: root.refresh()
    }
    Timer {
        id: refreshSoon
        interval: 1500
        onTriggered: { root.refresh(); root.scan(); }
    }

    Process {
        id: state
        command: ["sh", "-c", root.cli + "echo \"radio:$($c radio wifi)\"; $c -t -f ACTIVE,SIGNAL,SSID dev wifi 2>/dev/null | awk -F: '$1==\"yes\"{print \"active:\"$2\":\"substr($0, index($0,$3)); exit}'"]
        stdout: StdioCollector {
            onStreamFinished: {
                let ssid = "", signal = 0;
                for (const line of text.trim().split("\n")) {
                    if (line.startsWith("radio:"))
                        root.enabled = line.slice(6).trim() === "enabled";
                    else if (line.startsWith("active:")) {
                        const rest = line.slice(7);
                        const cut = rest.indexOf(":");
                        signal = parseInt(rest.slice(0, cut)) || 0;
                        ssid = rest.slice(cut + 1).replace(/\\:/g, ":");
                    }
                }
                root.ssid = ssid;
                root.signal = signal;
            }
        }
    }

    // In range: IN-USE, SIGNAL, SECURITY, SSID (last: it can hold colons, which nmcli escapes as "\:").
    Process {
        id: list
        command: ["sh", "-c", root.cli + "known=$($c -t -f NAME,TYPE connection show 2>/dev/null | awk -F: '$2 ~ /wireless/{print $1}'); "
            + "$c -t -f IN-USE,SIGNAL,SECURITY,SSID dev wifi list --rescan auto 2>/dev/null; echo '--known--'; printf '%s\\n' \"$known\""]
        stdout: StdioCollector {
            onStreamFinished: {
                const [listPart, knownPart] = text.split("--known--");
                const known = new Set((knownPart ?? "").trim().split("\n").filter(Boolean));
                const seen = new Map();
                for (const line of listPart.trim().split("\n")) {
                    const parts = root.fields(line);
                    if (parts.length < 4)
                        continue;
                    const ssid = parts.slice(3).join(":").replace(/\\:/g, ":");
                    if (!ssid)
                        continue;
                    const entry = { ssid, signal: parseInt(parts[1]) || 0, secure: parts[2] !== "" && parts[2] !== "--", active: parts[0] === "*", known: known.has(ssid) };
                    const prior = seen.get(ssid);
                    if (!prior || entry.active || entry.signal > prior.signal)
                        seen.set(ssid, entry);
                }
                root.networks = [...seen.values()].sort((a, b) => (b.active - a.active) || (b.known - a.known) || (b.signal - a.signal));
                root.scanning = false;
            }
        }
    }

    Process {
        id: join
        stderr: StdioCollector { id: joinErr }
        onExited: code => {
            if (code !== 0)
                root.error = (joinErr.text.trim().split("\n").pop() || "Could not connect").replace(/^Error: /, "");
            root.connecting = "";
            refreshSoon.restart();
        }
    }
}
