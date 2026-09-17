pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import qs.Config

/**
 * Spotlight's result list.
 *
 * Every query runs `halcyon search --json`, which is where the providers
 * actually live. Two things keep it feeling instant:
 *
 *   · a short debounce, so a fast typist causes one search rather than
 *     one per keystroke;
 *   · a generation counter, so a slow query that finishes after a newer
 *     one cannot overwrite the newer results.
 */
Singleton {
    id: root

    property string query: ""
    property var results: []
    property bool searching: false
    property int selected: 0

    /** Bumped per query; stale replies are dropped by comparing it. */
    property int generation: 0
    property int inFlight: -1

    readonly property int limit: Config.get("search.maxResults", 40)

    /** Results grouped by category, in the order they first appear. */
    readonly property var grouped: {
        const order = [];
        const buckets = ({});
        for (const result of root.results) {
            const key = result.category ?? "Results";
            if (buckets[key] === undefined) {
                buckets[key] = [];
                order.push(key);
            }
            buckets[key].push(result);
        }
        return order.map(name => ({ name: name, items: buckets[name] }));
    }

    function search(text: string): void {
        root.query = text;
        if (text.trim().length === 0) {
            root.results = [];
            root.selected = 0;
            root.searching = false;
            debounce.stop();
            return;
        }
        root.searching = true;
        debounce.restart();
    }

    /**
     * Search a restricted set of providers.
     *
     * Used by the clipboard shortcut, which wants the history and
     * nothing else — offering applications alongside clipboard entries
     * would make the same keystroke mean two things.
     */
    property var providerFilter: []

    function searchProviders(providers: var): void {
        root.providerFilter = providers ?? [];
        root.query = "";
        root.searching = true;
        root.dispatch();
    }

    function clear(): void {
        root.providerFilter = [];
        root.query = "";
        root.results = [];
        root.selected = 0;
        root.searching = false;
        debounce.stop();
    }

    function activate(index: int): void {
        const result = root.results[index >= 0 ? index : root.selected];
        if (!result)
            return;
        Quickshell.execDetached(
            Paths.command(["activate", JSON.stringify(result.activate)])
        );
    }

    function move(delta: int): void {
        if (root.results.length === 0)
            return;
        const next = root.selected + delta;
        // Clamp rather than wrap: wrapping from the last result back to
        // the first is disorienting when the list is long.
        root.selected = Math.max(0, Math.min(root.results.length - 1, next));
    }

    Timer {
        id: debounce
        // Long enough to swallow a burst of keystrokes, short enough that
        // it never feels like waiting.
        interval: 90
        onTriggered: root.dispatch()
    }

    function dispatch(): void {
        root.generation += 1;
        root.inFlight = root.generation;
        let args = ["search", root.query, "--json", "--limit", String(root.limit)];
        for (const provider of root.providerFilter)
            args = args.concat(["--provider", provider]);
        runner.command = Paths.command(args);
        runner.running = true;
    }

    Process {
        id: runner
        property int tag: 0

        onRunningChanged: {
            if (this.running)
                this.tag = root.inFlight;
        }

        stdout: StdioCollector {
            onStreamFinished: {
                // A reply from an older query would replace newer results
                // with stale ones; drop it instead.
                if (runner.tag !== root.generation)
                    return;
                try {
                    root.results = JSON.parse(this.text) ?? [];
                } catch (error) {
                    root.results = [];
                }
                root.selected = 0;
                root.searching = false;
            }
        }

        onExited: (code, status) => {
            if (runner.tag === root.generation)
                root.searching = false;
        }
    }
}
