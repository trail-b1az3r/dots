pragma Singleton

import QtQuick
import Quickshell
import qs.Config

/**
 * Which overlay is on screen.
 *
 * One place decides, because two overlays open at once is almost always
 * a bug — Spotlight over Control Center, the switcher over the overview.
 * Opening one closes the other, and every surface animates out properly
 * instead of vanishing.
 */
Singleton {
    id: root

    /** "" when nothing is open. */
    property string current: ""
    /** Arbitrary payload for the surface being opened. */
    property var payload: ({})

    /** Surfaces that may appear over the top of another one. */
    readonly property var alwaysOnTop: ["osd", "notifications"]

    signal opened(string name)
    signal closed(string name)
    signal requested(string name, string action, var args)

    function open(name: string, data: var): void {
        if (root.current === name && name !== "")
            return;
        if (root.current !== "" && root.current !== name)
            root.closed(root.current);
        root.payload = data ?? ({});
        root.current = name;
        root.opened(name);
    }

    function close(name: string): void {
        const target = (name && name.length > 0) ? name : root.current;
        if (root.current !== target)
            return;
        root.current = "";
        root.payload = ({});
        root.closed(target);
    }

    function toggle(name: string, data: var): void {
        if (root.current === name)
            root.close(name);
        else
            root.open(name, data);
    }

    function isOpen(name: string): bool {
        return root.current === name;
    }

    /** Ask an already-open surface to do something, e.g. focus a field. */
    function request(name: string, action: string, args: var): void {
        root.requested(name, action, args ?? ({}));
    }
}
