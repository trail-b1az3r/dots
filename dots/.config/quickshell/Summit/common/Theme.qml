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

    // The frost's own colour: the theme's surface with its hue taken out, as light or dark as it is. Glass tinted with
    // the surface itself took on the theme's colour (HyperNeo v2's navy turned every pane blue); the accent is kept for
    // what is active.
    readonly property color glass: Qt.hsla(0, 0, surface.hslLightness, 1)

    function alpha(colour, a) {
        return Qt.rgba(colour.r, colour.g, colour.b, a);
    }

    // Type and shape ---------------------------------------------------------------------------------------------
    // Text: Summit Sans (assets/fonts: Google Sans Flex with rounded ends, under its own name; OFL), unless Settings
    // or the theme names another. Code (keys, codes, the clipboard): Iosevka Nerd Font when it is installed
    // (ttf-iosevka-nerd), else JetBrains Mono's, else any monospace.
    // `halcyon fonts right-font` puts everything in RightFont until the next restart (a file in $XDG_RUNTIME_DIR,
    // which the next boot clears; `halcyon fonts right-font off` sooner).
    readonly property string font: rightFont ? rightFontName : (prefsText !== "" ? prefsText : (data.font ?? summitSansName))
    readonly property string mono: rightFont ? rightFontName : (prefsCode !== "" ? prefsCode : installedMono)
    readonly property string summitSansName: sans.status === FontLoader.Ready ? sans.name : "Summit Sans"
    readonly property string installedMono: {
        const families = Qt.fontFamilies();
        for (const f of ["Iosevka Nerd Font", "Iosevka Nerd Font Mono", "Iosevka", "JetBrainsMono Nerd Font", "JetBrains Mono"])
            if (families.includes(f))
                return f;
        return "monospace";
    }
    FontLoader {
        id: sans
        source: Qt.resolvedUrl("../assets/fonts/SummitSans.ttf")
    }

    property bool rightFont: false
    readonly property string rightFontName: rightFontLoader.status === FontLoader.Ready ? rightFontLoader.name : "RightFont Review"
    FontLoader {
        id: rightFontLoader
        source: root.rightFont ? "file://" + (Quickshell.env("XDG_DATA_HOME") || (Quickshell.env("HOME") + "/.local/share"))
                                 + "/fonts/halcyon-rightfont/RightFont-Review-v7.ttf" : ""
    }
    FileView {
        path: (Quickshell.env("XDG_RUNTIME_DIR") || "/tmp") + "/halcyon/right-font"
        watchChanges: true
        printErrors: false
        onFileChanged: reload()
        onLoaded: root.rightFont = true
        onLoadFailed: root.rightFont = false
    }

    // The fonts chosen in Settings (services/Prefs.qml has the rest of that file).
    property string prefsText: ""
    property string prefsCode: ""
    FileView {
        path: (Quickshell.env("XDG_CONFIG_HOME") || (Quickshell.env("HOME") + "/.config")) + "/halcyon/summit.json"
        watchChanges: true
        printErrors: false
        onFileChanged: reload()
        onLoaded: {
            try {
                const fonts = JSON.parse(text())?.fonts ?? {};
                root.prefsText = fonts.text ?? "";
                root.prefsCode = fonts.code ?? "";
            } catch (e) {
                root.prefsText = "";
                root.prefsCode = "";
            }
        }
        onLoadFailed: {
            root.prefsText = "";
            root.prefsCode = "";
        }
    }
    // The icons: Summit's own cut of Material Symbols Rounded (assets/fonts, Apache-2.0), with every icon it draws and
    // the font's fill and weight axes, so it never depends on the full font being installed (it is an AUR package).
    readonly property string iconFont: symbols.status === FontLoader.Ready ? symbols.name : "Material Symbols Rounded"
    FontLoader {
        id: symbols
        source: Qt.resolvedUrl("../assets/fonts/SummitSymbols.ttf")
    }
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
