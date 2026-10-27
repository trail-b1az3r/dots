pragma Singleton
pragma ComponentBehavior: Bound

import qs.modules.common
import qs.modules.common.functions
import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Hyprland

/**
 * A service that provides access to Hyprland keybinds.
 * Uses the `get_keybinds.py` script to parse comments in config files in a certain format and convert to JSON.
 */
Singleton {
    id: root
    property var keybinds: []
    property var keybindCategories: []

    // Super + Ctrl + Alt + Shift, what a Hyper key sends (halcyon/keybinds.lua), and Mod3, for one mapped to it.
    readonly property int hyperMask: (1 << 0) | (1 << 2) | (1 << 3) | (1 << 6)
    readonly property int mod3Mask: 1 << 5
    function isHyperChord(bind) {
        return ((bind.modmask ?? 0) & root.hyperMask) === root.hyperMask || ((bind.modmask ?? 0) & root.mod3Mask) !== 0;
    }
    /** A hypr key: a Hyper chord, or a bind of hypr mode (its submap, or described as one). The cheat sheet shows these
     *  on a page of their own. */
    function isHyprKey(bind) {
        return root.isHyperChord(bind) || bind.submap === "hypr" || (bind.description ?? "").startsWith("Hypr mode:");
    }
    /** Whether a bind is listed on a page: the Hypr keys page has the hypr keys and what turns hypr mode on and off
     *  (that one is on the Keybinds page too); the Keybinds page has everything else. */
    function onPage(bind, hyprPage) {
        if (hyprPage)
            return root.isHyprKey(bind) || /hypr mode/i.test(bind.description ?? "");
        return !root.isHyprKey(bind);
    }
    /** The categories of the binds on one page. */
    function categoriesOf(hyprOnly) {
        const groups = [];
        for (const bind of root.keybinds) {
            const description = bind.description ?? "";
            const group = description.substring(0, description.indexOf(":"));
            if (group.length > 0 && root.onPage(bind, hyprOnly) && !groups.includes(group))
                groups.push(group);
        }
        return groups;
    }

    Connections {
        target: Hyprland

        function onRawEvent(event) {
            if (event.name == "configreloaded") {
                getKeybinds.running = true
            }
        }
    }

    Process {
        id: getKeybinds
        running: true
        command: ["hyprctl", "binds", "-j"]
        
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    root.keybinds = JSON.parse(text)
                    var groups = []
                    for (var i = 0; i < root.keybinds.length; i++) {
                        var bind = root.keybinds[i].description
                        var group = bind.substring(0, bind.indexOf(":"))
                        if (!groups.includes(group) && group.length > 0) {
                            groups.push(group)
                        }
                    }
                    root.keybindCategories = groups
                } catch (e) {
                    console.error("[CheatsheetKeybinds] Error parsing keybinds:", e)
                }
            }
        }
    }
}

