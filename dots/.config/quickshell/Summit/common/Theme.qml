pragma Singleton
pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Io

/**
 * Summit's look: colours, type and sizes. The colours come from the active Halcyon theme (halcyon-theme writes them to
 * ~/.local/state/halcyon/summit.json when a theme runs Summit) and change with it; until then, HyperNeo v2's.
 */
Singleton {
    id: root

    readonly property string stateDir: (Quickshell.env("XDG_STATE_HOME") || (Quickshell.env("HOME") + "/.local/state")) + "/halcyon"
    property var data: ({})
    readonly property var c: data.colors ?? ({})

    // Colours ----------------------------------------------------------------------------------------------------
    readonly property color background: c.background ?? "#0B1322"
    readonly property color surface: c.surface ?? "#101A2C"
    readonly property color surfaceHigh: c.surface_high ?? "#18243A"
    readonly property color text: c.text ?? "#E8EDF6"
    readonly property color muted: c.muted ?? "#93A0B6"
    readonly property color accent: c.accent ?? "#9CC0FF"
    readonly property color accentText: c.accent_text ?? "#0B1A33"
    readonly property color warm: c.warm ?? "#E8C79A"
    readonly property color outline: c.outline ?? "#FFFFFF"
    // Frosted glass: how much of the surface colour tints the blurred wallpaper behind the bars, menus and popups.
    readonly property real glassTint: data.glass_tint ?? data.bar_opacity ?? 0.42
    readonly property real barOpacity: glassTint

    function alpha(colour, a) {
        return Qt.rgba(colour.r, colour.g, colour.b, a);
    }

    // Type and shape ---------------------------------------------------------------------------------------------
    readonly property string font: data.font ?? "Inter"
    readonly property string iconFont: "Material Symbols Rounded"
    readonly property int fontSize: 13
    readonly property int barHeight: 38
    readonly property int gap: 10
    readonly property int radius: 14
    readonly property int animMs: 180
    // Motion: a soft spring for things that move, a quick ease for colours and fades.
    readonly property real springStiffness: 3.2
    readonly property real springDamping: 0.26
    readonly property int enterMs: 420

    readonly property string wallpaper: data.wallpaper ?? ""

    FileView {
        path: root.stateDir + "/summit.json"
        watchChanges: true
        onFileChanged: reload()
        onLoaded: {
            try {
                root.data = JSON.parse(text()) ?? {};
            } catch (e) {
                root.data = {};
            }
        }
        onLoadFailed: root.data = {}
    }
}
