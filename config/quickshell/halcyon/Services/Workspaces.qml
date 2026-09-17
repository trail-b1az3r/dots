pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Hyprland
import qs.Config

/**
 * Workspaces and windows, from Hyprland's IPC.
 *
 * Presents the list the way a Spaces-style indicator needs it: a fixed
 * run of slots so the indicator does not reflow as workspaces come and
 * go, each annotated with whether it exists, is occupied, and where it
 * lives.
 */
Singleton {
    id: root

    readonly property var all: Hyprland.workspaces.values
    readonly property var toplevels: Hyprland.toplevels.values
    readonly property HyprlandWorkspace focused: Hyprland.focusedWorkspace
    readonly property HyprlandMonitor focusedMonitor: Hyprland.focusedMonitor
    readonly property int focusedId: root.focused?.id ?? 1

    readonly property int count: Math.max(1, Math.min(20, Config.get("workspaces.count", 10)))
    readonly property bool perMonitor: Config.get("workspaces.perMonitor", true)

    /** Fixed slots, so the indicator's width does not jump around. */
    readonly property var slots: {
        const names = Config.get("workspaces.names", ({}));
        const out = [];
        for (let index = 1; index <= root.count; index++) {
            const live = root.all.find(workspace => workspace.id === index) ?? null;
            out.push({
                id: index,
                name: names[String(index)] ?? (live?.name ?? String(index)),
                exists: live !== null,
                occupied: live !== null && (live.toplevels?.values.length ?? 0) > 0,
                windows: live !== null ? (live.toplevels?.values.length ?? 0) : 0,
                active: live !== null && live.active,
                focused: index === root.focusedId,
                urgent: live !== null && live.urgent,
                monitor: live?.monitor?.name ?? ""
            });
        }
        return out;
    }

    /** Special workspaces, which are not part of the numbered run. */
    readonly property var specials: root.all.filter(workspace => workspace.id < 0)

    function focus(id: int): void {
        Hyprland.dispatch("hl.dsp.focus({ workspace = " + id + " })");
    }

    function moveWindowTo(id: int): void {
        Hyprland.dispatch(
            "hl.dsp.window.move({ workspace = " + id + ", follow = true })"
        );
    }

    function focusWindow(address: string): void {
        Hyprland.dispatch('hl.dsp.focus({ window = "address:' + address + '" })');
    }

    function closeWindow(address: string): void {
        Hyprland.dispatch('hl.dsp.window.close({ window = "address:' + address + '" })');
    }

    function relative(delta: int): void {
        Hyprland.dispatch(
            'hl.dsp.focus({ workspace = "e' + (delta > 0 ? "+" : "") + delta + '" })'
        );
    }

    /** Windows on a workspace, in a stable order for the overview. */
    function windowsOn(id: int): var {
        return root.toplevels
            .filter(toplevel => toplevel.workspace?.id === id)
            .sort((a, b) => a.address.localeCompare(b.address));
    }
}
