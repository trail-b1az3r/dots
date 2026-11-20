import QtQuick
import QtTest
import Quickshell
import qs.services

// services/Niri.qml: niri's event stream turned into workspaces and windows, as the bar reads them.
Item {
    TestCase {
        name: "Niri"

        function init() {
            Quickshell.reset();
            Niri.handle({ WorkspacesChanged: { workspaces: [
                { id: 11, idx: 1, name: null, output: "DP-1", is_active: true, is_focused: true, active_window_id: 100 },
                { id: 12, idx: 2, name: null, output: "DP-1", is_active: false, is_focused: false, active_window_id: null },
                { id: 21, idx: 1, name: null, output: "HDMI-A-1", is_active: true, is_focused: false, active_window_id: 200 }
            ] } });
            Niri.handle({ WindowsChanged: { windows: [
                { id: 100, title: "Docs", app_id: "firefox", workspace_id: 11, is_focused: true, is_floating: false },
                { id: 200, title: "Shell", app_id: "Alacritty", workspace_id: 21, is_focused: false, is_floating: false }
            ] } });
        }

        function test_not_available_outside_niri() {
            verify(!Niri.available, "NIRI_SOCKET is not set in the test");
            Niri.focusWorkspace(2);
            compare(Quickshell.calls.length, 0, "no niri, no actions");
        }

        function test_workspaces_per_output_in_order() {
            compare(Niri.workspacesOn("DP-1").map(ws => ws.idx), [1, 2]);
            compare(Niri.workspacesOn("HDMI-A-1").length, 1);
            compare(Niri.activeIdxOn("DP-1"), 1);
            compare(Niri.focusedWorkspace.id, 11);
            compare(Niri.focusedWindow.app_id, "firefox");
        }

        function test_switching_workspace() {
            Niri.handle({ WorkspaceActivated: { id: 12, focused: true } });
            compare(Niri.activeIdxOn("DP-1"), 2);
            compare(Niri.focusedWorkspace.id, 12);
            verify(Niri.workspaces[21].is_active, "the other output keeps its workspace");
        }

        function test_windows_come_and_go() {
            Niri.handle({ WindowOpenedOrChanged: { window: { id: 300, title: "Notes", app_id: "kate", workspace_id: 12,
                                                             is_focused: true, is_floating: false } } });
            compare(Niri.focusedWindow.app_id, "kate");
            verify(!Niri.windows[100].is_focused, "focus moved off the old window");
            compare(Niri.windowsOnWorkspace(12).length, 1);
            Niri.handle({ WindowClosed: { id: 300 } });
            compare(Niri.focusedWindow, null);
            compare(Niri.windowsOnWorkspace(12).length, 0);
        }

        function test_the_button_shows_the_workspace_active_window() {
            compare(Niri.mainWindowOf(Niri.workspaceAt("HDMI-A-1", 1)).title, "Shell");
            compare(Niri.mainWindowOf(Niri.workspaceAt("DP-1", 2)), null);
            Niri.handle({ WorkspaceActiveWindowChanged: { workspace_id: 11, active_window_id: null } });
            compare(Niri.mainWindowOf(Niri.workspaceAt("DP-1", 1)).id, 100, "any window of it, then");
        }

        function test_focus_and_overview() {
            Niri.handle({ WindowFocusChanged: { id: 200 } });
            compare(Niri.focusedWindow.title, "Shell");
            Niri.handle({ OverviewOpenedOrClosed: { is_open: true } });
            verify(Niri.overviewOpen);
        }
    }
}
