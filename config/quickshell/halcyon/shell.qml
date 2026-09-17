//@ pragma ShellId halcyon
//@ pragma AppId org.halcyon.Shell
//@ pragma DropExpensiveFonts

import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Hyprland
import qs.Config
import qs.Services
import qs.Modules.Osd
import qs.Modules.Notifications
import qs.Modules.Spotlight
import qs.Modules.ControlCenter
import qs.Modules.Assistant
import qs.Modules.Overview
import qs.Modules.Switcher
import qs.Modules.PowerMenu
import qs.Modules.Calendar
import qs.Modules.Dashboard
import qs.Modules.Settings
import qs.Modules.Cheatsheet
import qs.Modules.Capture
import qs.Modules.Lock

/**
 * Halcyon — the Quickshell half of the desktop.
 *
 * Waybar owns the bar; this owns everything interactive: Spotlight,
 * Control Center, notifications, the HUD, Mission Control, the switcher,
 * the assistant, Settings and the lock screen.
 *
 * Two rules shape the structure:
 *
 *   · Surfaces are loaded lazily. Nineteen Settings panes and a dozen
 *     overlays instantiated at startup would cost memory and startup
 *     time for windows nobody has opened.
 *   · Every side effect goes through the `halcyon` CLI, not through a
 *     shell command built in QML. That is what keeps the keybinds, the
 *     bar and the panels doing exactly the same thing.
 */
ShellRoot {
    id: root

    // ── Always present ─────────────────────────────────────────────────
    //
    // The notification server has to be running before a notification
    // arrives, and the HUD has to be listening before a volume key is
    // pressed. Everything else waits until it is asked for.

    Osd { id: osd }
    Popups {}
    Lock { id: lockScreen }

    // ── On demand ──────────────────────────────────────────────────────

    LazyLoader {
        active: Overlays.isOpen("spotlight") || Overlays.current === "spotlight"
        Spotlight {}
    }

    LazyLoader {
        active: Overlays.isOpen("control")
        ControlCenter {}
    }

    LazyLoader {
        active: Overlays.isOpen("notifications")
        Centre {}
    }

    LazyLoader {
        active: Overlays.isOpen("assistant")
        AssistantPanel {}
    }

    LazyLoader {
        active: Overlays.isOpen("overview")
        Overview {}
    }

    LazyLoader {
        id: switcherLoader
        active: Overlays.isOpen("switcher")
        Switcher {}
    }

    LazyLoader {
        active: Overlays.isOpen("power")
        PowerMenu {}
    }

    LazyLoader {
        active: Overlays.isOpen("calendar")
        Calendar {}
    }

    LazyLoader {
        active: Overlays.isOpen("settings")
        Settings {}
    }

    LazyLoader {
        active: Overlays.isOpen("cheatsheet")
        Cheatsheet {}
    }

    LazyLoader {
        active: Overlays.isOpen("capture")
        Capture {}
    }

    // The desktop widgets stay loaded once shown, because they are part
    // of the desktop rather than a panel you dismiss.
    Dashboard {}

    // ── IPC ────────────────────────────────────────────────────────────
    //
    // Everything the keybinds and Waybar call. `qs -c halcyon ipc call
    // <target> <function>`, which is what `halcyon shell …` wraps.

    IpcHandler {
        target: "spotlight"

        function toggle(): void { Overlays.toggle("spotlight", ({})); }
        function open(): void { Overlays.open("spotlight", ({})); }
        function close(): void { Overlays.close("spotlight"); }
        function clipboard(): void { Overlays.open("spotlight", { mode: "clipboard" }); }
        function askAi(): void { Overlays.open("assistant", { listen: false }); }
        function search(query: string): void {
            Overlays.open("spotlight", ({}));
            Overlays.request("spotlight", "prefill", { text: query });
        }
    }

    IpcHandler {
        target: "control"

        function toggle(): void { Overlays.toggle("control", ({})); }
        function open(): void { Overlays.open("control", ({})); }
        function close(): void { Overlays.close("control"); }
        function network(): void { Overlays.open("control", { section: "wifi" }); }
        function bluetooth(): void { Overlays.open("control", { section: "bluetooth" }); }
        function audio(): void { Overlays.open("control", { section: "audio" }); }
    }

    IpcHandler {
        target: "notifications"

        function toggle(): void { Overlays.toggle("notifications", ({})); }
        function clear(): void { Notifications.clearAll(); }
        function setDoNotDisturb(value: bool): void { Notifications.setDoNotDisturb(value); }
        function count(): int { return Notifications.unread; }
    }

    IpcHandler {
        target: "osd"

        function show(kind: string): void { osd.show(kind); }
    }

    IpcHandler {
        target: "overview"

        function toggle(): void { Overlays.toggle("overview", ({})); }
    }

    IpcHandler {
        target: "switcher"

        function next(): void { root.switchApplication(1); }
        function previous(): void { root.switchApplication(-1); }
    }

    IpcHandler {
        target: "assistant"

        function toggle(): void { Overlays.toggle("assistant", ({})); }
        function listen(): void { Overlays.open("assistant", { listen: true }); }
        function ask(prompt: string): void {
            Overlays.open("assistant", { prompt: prompt });
        }
        function cancel(): void { Assistant.cancel(); }
    }

    IpcHandler {
        target: "power"

        function toggle(): void { Overlays.toggle("power", ({})); }
    }

    IpcHandler {
        target: "calendar"

        function toggle(): void { Overlays.toggle("calendar", ({})); }
    }

    IpcHandler {
        target: "dashboard"

        function toggle(): void { Overlays.toggle("dashboard", ({})); }
    }

    IpcHandler {
        target: "settings"

        function open(section: string): void {
            if (Overlays.isOpen("settings"))
                Overlays.request("settings", "section", { section: section });
            else
                Overlays.open("settings", { section: section });
        }
        function close(): void { Overlays.close("settings"); }
    }

    IpcHandler {
        target: "cheatsheet"

        function toggle(): void { Overlays.toggle("cheatsheet", ({})); }
    }

    IpcHandler {
        target: "capture"

        function toggle(): void { Overlays.toggle("capture", ({})); }
    }

    IpcHandler {
        target: "media"

        function toggle(): void { Overlays.toggle("control", { section: "audio" }); }
    }

    IpcHandler {
        target: "lock"

        function lock(): void { lockScreen.lock(); }
        function locked(): bool { return lockScreen.locked; }
    }

    IpcHandler {
        target: "shell"

        function reload(): void { Quickshell.reload(true); }
        function close(): void { Overlays.close(""); }
        function state(): string { return Overlays.current; }
    }

    function switchApplication(direction: int): void {
        // The switcher owns its own open/step logic, so it has to exist
        // before the first Tab rather than being created by it.
        switcherLoader.active = true;
        const instance = switcherLoader.item;
        if (instance)
            instance.open(direction);
    }

    // ── Global shortcuts ───────────────────────────────────────────────
    //
    // Registered through hyprland-global-shortcuts as well as the keybind
    // config, so the shell still answers if the generated Lua has not
    // been regenerated yet.

    GlobalShortcut {
        appid: "halcyon"
        name: "spotlight"
        description: "Open Spotlight"
        onPressed: Overlays.toggle("spotlight", ({}))
    }

    GlobalShortcut {
        appid: "halcyon"
        name: "assistant"
        description: "Talk to the assistant"
        onPressed: Overlays.open("assistant", { listen: true })
    }

    // ── Compositor events ──────────────────────────────────────────────

    Connections {
        target: Hyprland

        function onRawEvent(event: HyprlandEvent): void {
            // Closing overlays when the workspace changes stops a panel
            // from hanging over a desktop the user has already left.
            if (event.name === "workspace" || event.name === "focusedmon") {
                if (Overlays.current === "overview" || Overlays.current === "switcher")
                    return;
                if (Overlays.current.length > 0)
                    Overlays.close("");
            }
        }
    }

    Component.onCompleted: {
        // Publish the initial notification count so the bar is correct
        // from the moment the shell starts rather than after the first
        // notification.
        Notifications.publish();
    }
}
