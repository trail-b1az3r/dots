pragma Singleton
pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Io

/**
 * Summit's own settings: ~/.config/halcyon/summit.json, written by Settings (Super+I) while Summit is the shell and
 * read again whenever it changes. Anything missing has its default here. (The theme's colours, wallpaper and pinned
 * apps are a different file: ~/.local/state/halcyon/summit.json, which halcyon-theme writes; common/Theme.qml.)
 */
Singleton {
    id: root

    readonly property string path: (Quickshell.env("XDG_CONFIG_HOME") || (Quickshell.env("HOME") + "/.config")) + "/halcyon/summit.json"
    property var data: ({})

    // Notifications --------------------------------------------------------------------------------------------------
    // Popups in the top right corner (they all stay in the side menu either way).
    readonly property bool popups: data.notifications?.popups ?? true
    // The importance model (services/Importance.qml): an important notification opens under the clock instead.
    readonly property bool importantBanner: data.notifications?.important_banner ?? true
    // How sure the model must be: 0.5 is its own line; higher lets fewer through.
    readonly property real importantThreshold: data.notifications?.threshold ?? 0.6
    readonly property bool doNotDisturb: data.notifications?.do_not_disturb ?? false

    // The side menu --------------------------------------------------------------------------------------------------
    // Pushing the pointer against the right edge of the rightmost screen opens it (clicking the bar's right group
    // always does).
    readonly property bool edgeOpensMenu: data.side_menu?.edge ?? true
    readonly property int edgeDelay: data.side_menu?.edge_delay ?? 150

    // The bar --------------------------------------------------------------------------------------------------------
    // The brightness button on the left (scroll it; click for the slider).
    readonly property bool brightnessButton: data.bar?.brightness ?? true

    // Hypr mode: the glow round the screens while it is on (the card of its keys always shows).
    readonly property bool hyprModeGlow: data.hypr_mode?.glow ?? true

    // Fonts: empty is Summit's own (Summit Sans for text, Iosevka Nerd Font for code, when installed).
    readonly property string textFont: data.fonts?.text ?? ""
    readonly property string codeFont: data.fonts?.code ?? ""

    // Changes one setting, as "section.key", and saves the file.
    function set(key, value) {
        const parts = key.split(".");
        const next = JSON.parse(JSON.stringify(root.data ?? {}));
        let node = next;
        for (const part of parts.slice(0, -1)) {
            if (typeof node[part] !== "object" || node[part] === null)
                node[part] = {};
            node = node[part];
        }
        node[parts[parts.length - 1]] = value;
        root.data = next;
        file.setText(JSON.stringify(next, null, 2) + "\n");
    }

    FileView {
        id: file
        path: root.path
        watchChanges: true
        printErrors: false
        onFileChanged: reload()
        onLoaded: {
            try {
                const parsed = JSON.parse(text());
                root.data = parsed && typeof parsed === "object" ? parsed : {};
            } catch (e) {
                root.data = {};
            }
        }
        onLoadFailed: root.data = {}
    }
}
