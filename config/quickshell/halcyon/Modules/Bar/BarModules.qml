pragma Singleton

import QtQuick
import Quickshell

/**
 * The bar's module registry: id → file, plus what each one is.
 *
 * The layout in settings is three lists of ids, so this is the only
 * place that knows how an id becomes a component. Adding a module means
 * adding a file and one line here; nothing else in the bar changes.
 *
 * `catalogue` is what Settings shows when someone is choosing modules,
 * which is why the description lives here rather than inside each file —
 * listing the options must not mean instantiating them.
 */
Singleton {
    id: root

    readonly property var catalogue: [
        {
            id: "launcher",
            name: qsTr("Launcher"),
            description: qsTr("Opens Spotlight. The bar's leftmost button."),
            file: "modules/Launcher.qml"
        },
        {
            id: "workspaces",
            name: qsTr("Workspaces"),
            description: qsTr("Workspace indicators for this monitor."),
            file: "modules/Workspaces.qml"
        },
        {
            id: "activeWindow",
            name: qsTr("Active window"),
            description: qsTr("The focused application and its title."),
            file: "modules/ActiveWindow.qml"
        },
        {
            id: "clock",
            name: qsTr("Clock"),
            description: qsTr("Time, and the date on hover. Opens the calendar."),
            file: "modules/Clock.qml"
        },
        {
            id: "date",
            name: qsTr("Date"),
            description: qsTr("The date, as its own module."),
            file: "modules/DateModule.qml"
        },
        {
            id: "media",
            name: qsTr("Media"),
            description: qsTr("What is playing, with transport controls."),
            file: "modules/MediaModule.qml"
        },
        {
            id: "tray",
            name: qsTr("System tray"),
            description: qsTr("Status icons from running applications."),
            file: "modules/Tray.qml"
        },
        {
            id: "notifications",
            name: qsTr("Notifications"),
            description: qsTr("Unread count; opens the notification centre."),
            file: "modules/NotificationsModule.qml"
        },
        {
            id: "cpu",
            name: qsTr("CPU"),
            description: qsTr("Processor utilisation."),
            file: "modules/Cpu.qml"
        },
        {
            id: "memory",
            name: qsTr("Memory"),
            description: qsTr("Used memory as a percentage."),
            file: "modules/MemoryModule.qml"
        },
        {
            id: "temperature",
            name: qsTr("Temperature"),
            description: qsTr("CPU temperature. Hidden when no sensor exists."),
            file: "modules/Temperature.qml"
        },
        {
            id: "gpu",
            name: qsTr("GPU"),
            description: qsTr("Graphics utilisation, where the driver reports it."),
            file: "modules/Gpu.qml"
        },
        {
            id: "network",
            name: qsTr("Network"),
            description: qsTr("Connection state; opens the network panel."),
            file: "modules/Network.qml"
        },
        {
            id: "bluetooth",
            name: qsTr("Bluetooth"),
            description: qsTr("Adapter state; opens the Bluetooth panel."),
            file: "modules/Bluetooth.qml"
        },
        {
            id: "audio",
            name: qsTr("Audio"),
            description: qsTr("Output volume. Scroll to change, click to mute."),
            file: "modules/AudioModule.qml"
        },
        {
            id: "microphone",
            name: qsTr("Microphone"),
            description: qsTr("Input mute state."),
            file: "modules/Microphone.qml"
        },
        {
            id: "battery",
            name: qsTr("Battery"),
            description: qsTr("Charge and time remaining. Hidden on a desktop."),
            file: "modules/BatteryModule.qml"
        },
        {
            id: "powerProfile",
            name: qsTr("Power profile"),
            description: qsTr("The active profile. Click to cycle."),
            file: "modules/PowerProfile.qml"
        },
        {
            id: "clipboard",
            name: qsTr("Clipboard"),
            description: qsTr("Opens clipboard history."),
            file: "modules/Clipboard.qml"
        },
        {
            id: "hypernix",
            name: qsTr("HyperNix"),
            description: qsTr("Generation and job state."),
            file: "modules/HyperNixModule.qml"
        },
        {
            id: "assistant",
            name: qsTr("AI assistant"),
            description: qsTr("Opens the assistant sidebar."),
            file: "modules/AssistantModule.qml"
        },
        {
            id: "settings",
            name: qsTr("Settings"),
            description: qsTr("Opens Halcyon settings."),
            file: "modules/SettingsModule.qml"
        },
        {
            id: "systemMenu",
            name: qsTr("System menu"),
            description: qsTr("Control Center, and the power menu on right-click."),
            file: "modules/SystemMenu.qml"
        },
        {
            id: "spacer",
            name: qsTr("Spacer"),
            description: qsTr("Flexible gap, for pushing modules apart."),
            file: "modules/Spacer.qml"
        },
        {
            id: "separator",
            name: qsTr("Separator"),
            description: qsTr("A thin dividing line."),
            file: "modules/SeparatorModule.qml"
        }
    ]

    readonly property var byId: {
        const map = ({});
        for (const entry of root.catalogue) {
            map[entry.id] = entry;
        }
        return map;
    }

    /** The QML file for an id, or "" when the id is not one we know. */
    function source(moduleId: string): string {
        const entry = root.byId[moduleId];
        return entry ? entry.file : "";
    }

    function known(moduleId: string): bool {
        return root.byId[moduleId] !== undefined;
    }

    function describe(moduleId: string): string {
        const entry = root.byId[moduleId];
        return entry ? entry.description : "";
    }

    function displayName(moduleId: string): string {
        const entry = root.byId[moduleId];
        return entry ? entry.name : moduleId;
    }
}
