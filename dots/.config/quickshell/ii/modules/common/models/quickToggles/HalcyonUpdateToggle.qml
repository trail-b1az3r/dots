import QtQuick
import Quickshell
import Quickshell.Io
import qs
import qs.services
import qs.modules.common
import qs.modules.common.functions

// Gets the newest Halcyon changes: `update apply` copies only what changed and reloads
// just those parts. Lit while `update check` has found commits waiting.
QuickToggleModel {
    id: model

    name: Translation.tr("Update Halcyon")
    hasStatusText: false
    icon: "system_update"
    property bool updateAvailable: false
    toggled: updateAvailable
    readonly property string updater: `${FileUtils.trimFileProtocol(Directories.config)}/hypr/hyprland/halcyon/update`

    mainAction: () => {
        Quickshell.execDetached([model.updater, "apply"]);
        model.updateAvailable = false;
        stateTimer.restart();
    }

    Process {
        id: stateCheck
        command: ["bash", "-c", "test -f \"${XDG_STATE_HOME:-$HOME/.local/state}/halcyon/update-available\""]
        onExited: (exitCode, exitStatus) => {
            model.updateAvailable = exitCode === 0;
        }
    }

    Timer {
        id: stateTimer
        interval: 60000
        running: true
        repeat: true
        triggeredOnStart: true
        onTriggered: stateCheck.running = true
    }

    tooltipText: updateAvailable ? Translation.tr("Update Halcyon (updates waiting)") : Translation.tr("Update Halcyon")
}
