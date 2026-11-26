pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io

/**
 * Which desktop shell runs now: what halcyon-theme last recorded in ~/.local/state/halcyon/desktop-shell
 * ("Halcyon", "Summit", "MacShell", "Noctalia"; empty: the Halcyon shell). Settings uses it to show Summit's own page,
 * and to leave out what only the Halcyon shell can do, while Summit is the shell. Read at once (Settings lays its
 * pages out from it).
 */
Singleton {
    id: root
    property string name: ""
    readonly property bool summit: root.name === "Summit"

    FileView {
        path: (Quickshell.env("XDG_STATE_HOME") || (Quickshell.env("HOME") + "/.local/state")) + "/halcyon/desktop-shell"
        blockLoading: true
        watchChanges: true
        printErrors: false
        onFileChanged: reload()
        onLoaded: root.name = text().trim()
        onLoadFailed: root.name = ""
    }
}
