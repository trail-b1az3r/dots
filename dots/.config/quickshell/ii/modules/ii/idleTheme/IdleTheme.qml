import qs.modules.common
import qs.modules.common.functions
import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland

/**
 * A new theme while you are away (Settings > Halcyon > When you are away): after `minutes` with no keyboard or mouse,
 * switch to the next theme, a random one, or one chosen theme; with `every`, keep switching that often while away;
 * with `restore`, put the theme from before back when you return. Video players and server mode (idle inhibitors)
 * hold it off, as they hold off the lock.
 */
Scope {
    id: root

    readonly property var settings: Config.options.halcyon.idleTheme
    readonly property string tool: `${FileUtils.trimFileProtocol(Directories.config)}/hypr/hyprland/halcyon/halcyon-theme`
    property var themeIds: []
    // The theme in use when you left ("" for none); null while you are here.
    property var before: null

    /** The theme to switch to: the one after `current` in `ids`, a random other one, or the chosen one. */
    function pick(mode, current, ids, chosen) {
        if (mode === "one")
            return chosen !== "" && chosen !== current ? chosen : "";
        const others = ids.filter(id => id !== current);
        if (others.length === 0)
            return "";
        if (mode === "random")
            return others[Math.floor(Math.random() * others.length)];
        const at = ids.indexOf(current);
        return ids[(at + 1) % ids.length] === current ? others[0] : ids[(at + 1) % ids.length];
    }

    function switchTheme() {
        const next = root.pick(root.settings.mode, Config.options.halcyon.theme ?? "", root.themeIds, root.settings.theme);
        if (next !== "")
            Quickshell.execDetached([root.tool, "apply", next]);
    }

    IdleMonitor {
        id: monitor
        enabled: root.settings.enable
        respectInhibitors: true
        timeout: Math.max(1, root.settings.minutes) * 60
        onIsIdleChanged: {
            if (isIdle) {
                root.before = Config.options.halcyon.theme ?? "";
                listProc.running = true;    // switches once the list is in
            } else {
                awayTimer.stop();
                if (root.settings.restore && root.before !== null && root.before !== (Config.options.halcyon.theme ?? "")) {
                    if (root.before === "")
                        Quickshell.execDetached([root.tool, "off"]);
                    else
                        Quickshell.execDetached([root.tool, "apply", root.before]);
                }
                root.before = null;
            }
        }
    }

    Timer {
        id: awayTimer
        interval: Math.max(1, root.settings.every) * 60 * 1000
        repeat: true
        onTriggered: root.switchTheme()
    }

    Process {
        id: listProc
        command: [root.tool, "list", "--json"]
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    root.themeIds = (JSON.parse(this.text).themes ?? []).map(t => t.id);
                } catch (error) {
                    root.themeIds = [];
                }
                if (!monitor.isIdle)
                    return;
                root.switchTheme();
                if (root.settings.every > 0)
                    awayTimer.restart();
            }
        }
    }
}
