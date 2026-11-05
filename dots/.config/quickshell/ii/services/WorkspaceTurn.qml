pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Hyprland

/**
 * Going to a workspace from the shell (the bar's workspaces, its scrolling). In Manga Ink the screen turns over like a
 * book's page as you go (modules/ii/pageTurn/PageTurn.qml, which registers itself here as the turner); otherwise, and
 * whenever it is not there, the workspace is simply focused.
 */
Singleton {
    id: root

    property var turner: null

    function go(target: int): void {
        if (target < 1)
            return;
        if (turner && turner.enabled)
            turner.turnTo(target);
        else
            Hyprland.dispatch(`hl.dsp.focus({workspace = ${target}})`);
    }

    /** The next (+1) or previous (-1) workspace on the focused monitor. */
    function step(direction: int): void {
        if (turner && turner.enabled)
            go((HyprlandData.monitors.find(m => m.focused)?.activeWorkspace?.id ?? 1) + direction);
        else
            Hyprland.dispatch(`hl.dsp.focus({workspace = "${direction > 0 ? "r+1" : "r-1"}"})`);
    }
}
