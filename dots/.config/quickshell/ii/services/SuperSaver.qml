pragma Singleton

import qs.modules.common
import qs.modules.common.functions
import QtQuick
import Quickshell
import Quickshell.Io

/**
 * The super battery saver (`halcyon saver`, halcyon_saver.py): 12 fps, 20% brightness, the power-saver profile, and
 * Wi-Fi that only reconnects after boot, waking, locking, unlocking or when you pick a network. It is on while
 * ~/.local/state/halcyon/saver.json exists, which this watches, so a change from the terminal shows here too.
 */
Singleton {
    id: root

    readonly property string tool: `${FileUtils.trimFileProtocol(Directories.config)}/hypr/hyprland/halcyon/halcyon_saver.py`
    readonly property string stateFile: `${Quickshell.env("XDG_STATE_HOME") || Quickshell.env("HOME") + "/.local/state"}/halcyon/saver.json`
    property bool active: false
    property bool busy: toggleProc.running

    function toggle() {
        if (toggleProc.running)
            return;
        toggleProc.command = [root.tool, root.active ? "off" : "on"];
        toggleProc.running = true;
    }

    FileView {
        id: stateView
        path: root.stateFile
        watchChanges: true
        printErrors: false
        onLoaded: root.active = true
        onLoadFailed: root.active = false
        onFileChanged: reload()
    }

    Process {
        id: toggleProc
        onExited: stateView.reload()
    }
}
