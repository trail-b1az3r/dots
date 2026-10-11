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

    /** Where the installer puts shipped assets. Honours HALCYON_DATA_DIR,
     *  the same override install.sh and the CLI use, so a custom install
     *  still finds its own logo. */
    readonly property string shareDir: {
        const override = Quickshell.env("HALCYON_DATA_DIR");
        return (override && override.length > 0) ? override : root.dataHome + "/halcyon";
    }

    /** The Halcyon mark as a PNG. The shell loads the PNG rather than the
     *  SVG master: Qt's PNG loader is always present, its SVG one is not. */
    readonly property string logo: root.shareDir + "/icons/halcyon.png"

    /** The halcyon CLI. Every side effect in the shell goes through it. */
    readonly property string cli: "halcyon"

    /** Build an argv list for the CLI — never a shell string. */
    function command(args: var): var {
        return [root.cli].concat(args);
    }
}
