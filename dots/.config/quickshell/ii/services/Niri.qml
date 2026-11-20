pragma Singleton
pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Io

/**
 * Niri, when the shell runs under it (niri sets NIRI_SOCKET): its workspaces and windows, kept up to date from
 * `niri msg --json event-stream`, and its actions. Under Hyprland `available` is false and nothing runs.
 *
 * Niri's workspaces are per output and numbered by position (idx, from 1), with one empty workspace kept at the end
 * of each output. A window's workspace_id is the workspace's id, which is not its idx.
 */
Singleton {
    id: root

    readonly property bool available: (Quickshell.env("NIRI_SOCKET") ?? "") !== ""

    // id -> workspace { id, idx, name, output, is_active, is_focused, active_window_id }
    property var workspaces: ({})
    // id -> window { id, title, app_id, workspace_id, is_focused, is_floating }
    property var windows: ({})
    property var focusedWindowId: null
    property bool overviewOpen: false

    readonly property var focusedWindow: focusedWindowId !== null ? (windows[focusedWindowId] ?? null) : null
    readonly property var focusedWorkspace: Object.values(workspaces).find(ws => ws.is_focused) ?? null

    /** The workspaces on one output (all of them for ""), in order. */
    function workspacesOn(output) {
        return Object.values(root.workspaces)
            .filter(ws => output === "" || ws.output === output)
            .sort((a, b) => a.idx - b.idx);
    }
    /** The idx of the workspace shown on an output (the focused one's for ""), 1 when unknown. */
    function activeIdxOn(output) {
        const ws = Object.values(root.workspaces).find(w => (output === "" ? w.is_focused : (w.output === output && w.is_active)));
        return ws ? ws.idx : 1;
    }
    function workspaceAt(output, idx) {
        return root.workspacesOn(output).find(ws => ws.idx === idx) ?? null;
    }
    function windowsOnWorkspace(workspaceId) {
        return Object.values(root.windows).filter(w => w.workspace_id === workspaceId);
    }
    /** The window a workspace button shows: the workspace's active window, or else any of its windows. */
    function mainWindowOf(workspace) {
        if (!workspace)
            return null;
        if (workspace.active_window_id !== null && workspace.active_window_id !== undefined && root.windows[workspace.active_window_id])
            return root.windows[workspace.active_window_id];
        return root.windowsOnWorkspace(workspace.id)[0] ?? null;
    }

    /** `niri msg action ...`, e.g. action(["focus-workspace", "3"]). */
    function action(args) {
        if (!root.available)
            return;
        Quickshell.execDetached(["niri", "msg", "action", ...args.map(String)]);
    }
    function focusWorkspace(idx) {
        root.action(["focus-workspace", idx]);
    }

    function setWorkspaces(list) {
        const map = {};
        for (const ws of list)
            map[ws.id] = ws;
        root.workspaces = map;
    }
    function setWindows(list) {
        const map = {};
        for (const w of list)
            map[w.id] = w;
        root.windows = map;
        const focused = list.find(w => w.is_focused);
        root.focusedWindowId = focused ? focused.id : null;
    }
    function handle(event) {
        if (event.WorkspacesChanged) {
            root.setWorkspaces(event.WorkspacesChanged.workspaces);
        } else if (event.WorkspaceActivated) {
            const { id, focused } = event.WorkspaceActivated;
            const output = root.workspaces[id]?.output;
            const map = Object.assign({}, root.workspaces);
            for (const key in map) {
                const ws = Object.assign({}, map[key]);
                if (ws.output === output)
                    ws.is_active = ws.id === id;
                if (focused)
                    ws.is_focused = ws.id === id;
                map[key] = ws;
            }
            root.workspaces = map;
        } else if (event.WorkspaceActiveWindowChanged) {
            const { workspace_id, active_window_id } = event.WorkspaceActiveWindowChanged;
            if (root.workspaces[workspace_id]) {
                const map = Object.assign({}, root.workspaces);
                map[workspace_id] = Object.assign({}, map[workspace_id], { active_window_id: active_window_id });
                root.workspaces = map;
            }
        } else if (event.WindowsChanged) {
            root.setWindows(event.WindowsChanged.windows);
        } else if (event.WindowOpenedOrChanged) {
            const w = event.WindowOpenedOrChanged.window;
            const map = Object.assign({}, root.windows);
            if (w.is_focused) {
                for (const key in map)
                    map[key] = Object.assign({}, map[key], { is_focused: false });
                root.focusedWindowId = w.id;
            }
            map[w.id] = w;
            root.windows = map;
        } else if (event.WindowClosed) {
            const map = Object.assign({}, root.windows);
            delete map[event.WindowClosed.id];
            root.windows = map;
            if (root.focusedWindowId === event.WindowClosed.id)
                root.focusedWindowId = null;
        } else if (event.WindowFocusChanged) {
            const id = event.WindowFocusChanged.id;
            const map = Object.assign({}, root.windows);
            for (const key in map)
                map[key] = Object.assign({}, map[key], { is_focused: map[key].id === id });
            root.windows = map;
            root.focusedWindowId = id;
        } else if (event.OverviewOpenedOrClosed) {
            root.overviewOpen = event.OverviewOpenedOrClosed.is_open;
        }
    }

    Process {
        id: stream
        running: root.available
        command: ["niri", "msg", "--json", "event-stream"]
        stdout: SplitParser {
            onRead: line => {
                try {
                    root.handle(JSON.parse(line));
                } catch (e) {
                    console.warn("[Niri] could not read an event:", e);
                }
            }
        }
        // niri restarted, or the stream broke: start it again (it begins with the full state).
        onExited: restart.restart()
    }
    Timer {
        id: restart
        interval: 1000
        onTriggered: stream.running = root.available
    }
}
