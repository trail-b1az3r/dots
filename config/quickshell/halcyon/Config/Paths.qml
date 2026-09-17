pragma Singleton

import QtQuick
import Quickshell

/**
 * Where Halcyon's files live.
 *
 * Resolved once, here, so no other file has to know whether the user set
 * XDG_CONFIG_HOME or the shell was started from an unusual directory.
 */
Singleton {
    id: root

    readonly property string home: Quickshell.env("HOME") ?? "/root"

    readonly property string configHome: {
        const xdg = Quickshell.env("XDG_CONFIG_HOME");
        return (xdg && xdg.length > 0) ? xdg : root.home + "/.config";
    }

    readonly property string stateHome: {
        const xdg = Quickshell.env("XDG_STATE_HOME");
        return (xdg && xdg.length > 0) ? xdg : root.home + "/.local/state";
    }

    readonly property string dataHome: {
        const xdg = Quickshell.env("XDG_DATA_HOME");
        return (xdg && xdg.length > 0) ? xdg : root.home + "/.local/share";
    }

    readonly property string halcyon: root.configHome + "/halcyon"
    readonly property string generated: root.halcyon + "/generated"
    readonly property string settingsFile: root.halcyon + "/settings.json"
    readonly property string themeFile: root.generated + "/theme.json"
    readonly property string paletteFile: root.generated + "/palette.json"
    readonly property string state: root.stateHome + "/halcyon"

    /** The halcyon CLI. Every side effect in the shell goes through it. */
    readonly property string cli: "halcyon"

    /** Build an argv list for the CLI — never a shell string. */
    function command(args: var): var {
        return [root.cli].concat(args);
    }
}
