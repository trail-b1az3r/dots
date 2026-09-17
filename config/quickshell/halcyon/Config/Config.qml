pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import qs.Config

/**
 * The user's settings, live.
 *
 * Reads settings.json and re-reads it whenever it changes, so the
 * Settings app does not need to tell every panel what it did — it writes
 * the file, and the shell follows.
 *
 * Every accessor has a default, because a fresh install has no file yet
 * and a half-written one must not take the desktop down.
 */
Singleton {
    id: root

    property var data: ({})
    readonly property bool loaded: Object.keys(root.data).length > 0

    // Convenience roots. Written as functions of `data` so they update
    // together the moment the file is re-read.
    readonly property var appearance: root.data.appearance ?? ({})
    readonly property var glass: root.data.glass ?? ({})
    readonly property var motion: root.data.motion ?? ({})
    readonly property var bar: root.data.bar ?? ({})
    readonly property var workspaces: root.data.workspaces ?? ({})
    readonly property var notifications: root.data.notifications ?? ({})
    readonly property var power: root.data.power ?? ({})
    readonly property var assistant: root.data.assistant ?? ({})
    readonly property var hypernix: root.data.hypernix ?? ({})
    readonly property var search: root.data.search ?? ({})
    readonly property var accessibility: root.data.accessibility ?? ({})
    readonly property var applications: root.data.applications ?? ({})
    readonly property var privacy: root.data.privacy ?? ({})
    readonly property var wallpaper: root.data.wallpaper ?? ({})

    /** Read a dotted path with a fallback, e.g. `get("glass.opacity", 0.6)`. */
    function get(path: string, fallback: var): var {
        const parts = path.split(".");
        let node = root.data;
        for (let i = 0; i < parts.length; i++) {
            if (node === undefined || node === null || typeof node !== "object")
                return fallback;
            node = node[parts[i]];
        }
        return node === undefined || node === null ? fallback : node;
    }

    /**
     * Write a setting.
     *
     * Goes through the CLI rather than writing JSON from QML: one writer
     * means no torn files, and the CLI also re-runs the theme pipeline so
     * Hyprland and Waybar hear about the change too.
     */
    function set(path: string, value: var): void {
        const text = (typeof value === "string") ? value : JSON.stringify(value);
        writer.command = Paths.command(["settings", "set", path, text]);
        writer.running = true;
    }

    function unset(path: string): void {
        writer.command = Paths.command(["settings", "unset", path]);
        writer.running = true;
    }

    function applyPreset(name: string): void {
        writer.command = Paths.command(["theme", "preset", name]);
        writer.running = true;
    }

    Process {
        id: writer
        // Settings writes are fire-and-forget; the file watcher below is
        // what tells the shell the change landed.
    }

    FileView {
        id: file
        path: Paths.settingsFile
        watchChanges: true
        printErrors: false

        onFileChanged: this.reload()
        onLoaded: root.parse(this.text())
        onLoadFailed: error => {
            // No settings file yet is the normal state on first run.
            if (error !== FileViewError.FileNotFound)
                console.warn("halcyon: could not read settings.json:", error);
        }
    }

    function parse(text: string): void {
        if (!text || text.length === 0)
            return;
        try {
            root.data = JSON.parse(text);
        } catch (error) {
            // Keep the last good settings rather than blanking the shell
            // while someone is mid-edit in a text editor.
            console.warn("halcyon: settings.json is not valid JSON:", error);
        }
    }
}
