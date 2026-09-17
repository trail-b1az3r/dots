pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Hyprland
import qs.Config

/**
 * Everything the shell does to the system, in one place.
 *
 * The rule is that QML never builds a shell command. It calls a function
 * here, which runs `halcyon` with an argv list — the same CLI the
 * keybinds and Waybar use, with the same validation and the same
 * allow-list. A bug in a panel cannot become a command injection, and
 * anything the shell can do can also be done from a terminal.
 */
Singleton {
    id: root

    /** Fire-and-forget. Nothing in the UI waits on the result. */
    function run(args: var): void {
        Quickshell.execDetached(Paths.command(args));
    }

    /** Run and hand stdout to a callback. Used for anything we display. */
    function capture(args: var, callback: var): void {
        const process = readerComponent.createObject(root, {
            argv: Paths.command(args),
            callback: callback
        });
        process.start();
    }

    /** A Hyprland dispatcher, for things the CLI has no reason to wrap. */
    function dispatch(expression: string): void {
        Hyprland.dispatch(expression);
    }

    // ── Shortcuts used across the shell ────────────────────────────────

    function setVolume(percent: int): void { root.run(["audio", "volume", String(percent)]); }
    function muteOutput(): void { root.run(["audio", "mute", "toggle"]); }
    function muteInput(): void { root.run(["audio", "mic", "toggle"]); }
    function setBrightness(percent: int): void { root.run(["backlight", String(percent)]); }
    function media(command: string): void { root.run(["media", command]); }

    function invoke(action: string, params: var): void {
        const args = ["action", action];
        for (const key in params)
            args.push(key + "=" + String(params[key]));
        root.run(args);
    }

    function activate(payload: var): void {
        root.run(["activate", JSON.stringify(payload)]);
    }

    function openSettings(section: string): void {
        Overlays.open("settings", { section: section });
    }

    function screenshot(mode: string): void { root.run(["screenshot", mode]); }
    function record(command: string): void { root.run(["record", command]); }
    function lock(): void { root.run(["session", "lock"]); }
    function wallpaperNext(): void { root.run(["wallpaper", "next"]); }
    function toggleMode(): void { root.run(["theme", "toggle-mode"]); }
    function powerProfile(name: string): void { root.run(["power", "profile", name]); }
    function setDoNotDisturb(value: bool): void {
        root.run(["notify", "dnd", value ? "on" : "off"]);
    }

    Component {
        id: readerComponent

        Process {
            id: process
            property var argv: []
            property var callback: null

            command: process.argv
            stdout: StdioCollector {
                onStreamFinished: {
                    if (process.callback)
                        process.callback(this.text);
                    process.destroy();
                }
            }

            function start(): void { this.running = true; }

            onExited: (code, status) => {
                if (code !== 0 && process.callback) {
                    process.callback("");
                    process.destroy();
                }
            }
        }
    }
}
