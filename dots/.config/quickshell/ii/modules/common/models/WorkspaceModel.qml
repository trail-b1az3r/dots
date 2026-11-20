import QtQuick
import Quickshell.Wayland
import Quickshell.Hyprland
import qs.services
import qs.modules.common as C

NestableObject {
    id: root

    required property HyprlandMonitor monitor
    // Under niri (services/Niri.qml): the output this model is for, and niri's workspaces on it, numbered from 1.
    property string screenName: ""
    readonly property bool niri: Niri.available
    readonly property var liveMonitorData: niri ? null : HyprlandData.monitors.find(m => m.id === monitor?.id)
    readonly property Toplevel activeWindow: ToplevelManager.activeToplevel
    readonly property int activeWorkspace: niri ? Niri.activeIdxOn(screenName) : (monitor?.activeWorkspace?.id ?? 1)
    readonly property bool currentWorkspaceNotFake: activeWindow?.activated ?? false // Active empty workspace = fake. At least, that's how I like to call it.
    readonly property int fakeWorkspace: currentWorkspaceNotFake ? -9999 : activeWorkspace
    readonly property int shownCount: C.Config.options.bar.workspaces.shown
    readonly property int group: Math.floor((activeWorkspace - 1) / shownCount)
    readonly property var specialWorkspace: liveMonitorData?.specialWorkspace
    readonly property string specialWorkspaceName: specialWorkspace?.name.replace("special:", "") ?? "special"
    readonly property bool specialWorkspaceActive: specialWorkspaceName !== ""

    property list<bool> occupied: []
    property list<var> biggestWindow: occupied.map((_, index) => {
        const wsId = getWorkspaceIdAt(index);
        if (root.niri) {
            // niri: the workspace's active window, in the shape the buttons read (class, title).
            const w = Niri.mainWindowOf(Niri.workspaceAt(root.screenName, wsId));
            return w ? { class: w.app_id ?? "", title: w.title ?? "" } : null;
        }
        var biggestWindow = HyprlandData.biggestWindowForWorkspace(wsId);
        return biggestWindow;
    })

    function getWorkspaceId(group, index) {
        return group * root.shownCount + index + 1;
    }
    function getWorkspaceIdAt(index) {
        return root.getWorkspaceId(root.group, index);
    }

    // Function to update workspaceOccupied
    function updateWorkspaceOccupied() {
        root.occupied = Array.from({
            length: root.shownCount
        }, (_, i) => {
            const thisWorkspaceId = getWorkspaceId(root.group, i);
            if (root.niri) {
                const ws = Niri.workspaceAt(root.screenName, thisWorkspaceId);
                return ws !== null && Niri.windowsOnWorkspace(ws.id).length > 0;
            }
            return Hyprland.workspaces.values.some(ws => ws.id === thisWorkspaceId);
        });
    }

    // Occupied workspace updates
    Component.onCompleted: updateWorkspaceOccupied()
    Connections {
        target: Hyprland.workspaces
        function onValuesChanged() {
            root.updateWorkspaceOccupied();
        }
    }
    Connections {
        target: Hyprland
        function onFocusedWorkspaceChanged() {
            root.updateWorkspaceOccupied();
        }
    }
    Connections {
        target: Niri
        enabled: root.niri
        function onWorkspacesChanged() {
            root.updateWorkspaceOccupied();
        }
        function onWindowsChanged() {
            root.updateWorkspaceOccupied();
        }
    }
    onGroupChanged: {
        updateWorkspaceOccupied();
    }
}
