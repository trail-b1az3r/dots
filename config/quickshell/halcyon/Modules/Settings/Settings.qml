import QtQuick
import QtQuick.Layouts
import Quickshell
import qs.Config
import qs.Components
import qs.Services

/**
 * Settings.
 *
 * Every control here writes through `Config.set`, which calls the CLI,
 * which rewrites the generated files and reloads whatever needs it. That
 * is why a change takes effect immediately in Hyprland and Waybar as
 * well as in the shell — there is one path, and this is the front of it.
 *
 * Nothing in this application edits a configuration file by hand, and
 * neither should you have to.
 */
OverlayWindow {
    id: root

    name: "settings"
    namespaceName: "halcyon-overlay"
    origin: "center"
    grabKeyboard: true

    property string section: "appearance"

    onOpened: {
        const requested = Overlays.payload.section ?? "";
        if (requested.length > 0)
            root.section = requested;
    }

    Connections {
        target: Overlays
        function onRequested(name: string, action: string, args: var): void {
            if (name === root.name && action === "section")
                root.section = args.section ?? root.section;
        }
    }

    readonly property var sections: [
        { id: "appearance", title: "Appearance", glyph: "󰸌" },
        { id: "glass", title: "Liquid Glass", glyph: "󰠱" },
        { id: "wallpaper", title: "Wallpaper", glyph: "󰸉" },
        { id: "animations", title: "Animations", glyph: "󰑮" },
        { id: "keybinds", title: "Keyboard", glyph: "󰌌" },
        { id: "workspaces", title: "Workspaces", glyph: "󰕰" },
        { id: "displays", title: "Displays", glyph: "󰍹" },
        { id: "audio", title: "Audio", glyph: "󰕾" },
        { id: "network", title: "Network", glyph: "󰖩" },
        { id: "bluetooth", title: "Bluetooth", glyph: "󰂯" },
        { id: "notifications", title: "Notifications", glyph: "󰂚" },
        { id: "battery", title: "Battery", glyph: "󰁹" },
        { id: "performance", title: "Performance", glyph: "󰓅" },
        { id: "assistant", title: "AI Assistant", glyph: "󰚩" },
        { id: "hypernix", title: "HyperNix", glyph: "󰆧" },
        { id: "applications", title: "Applications", glyph: "󰣆" },
        { id: "privacy", title: "Privacy", glyph: "󰒃" },
        { id: "accessibility", title: "Accessibility", glyph: "󰖳" },
        { id: "about", title: "About", glyph: "󰋽" }
    ]

    GlassSurface {
        anchors.centerIn: parent
        width: Math.min(940, root.width - Theme.spacingXl * 2)
        height: Math.min(680, root.height - Theme.spacingXl * 2)
        level: 4
        radius: Theme.radiusXl
        padding: 0
        clipContent: true

        RowLayout {
            anchors.fill: parent
            spacing: 0

            // ── Sidebar ──────────────────────────────────────────────

            Rectangle {
                Layout.preferredWidth: 216
                Layout.fillHeight: true
                color: Theme.surfaceSunken

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spacingSm
                    spacing: Theme.spacingXs

                    Label {
                        Layout.fillWidth: true
                        Layout.margins: Theme.spacingSm
                        text: "Settings"
                        variant: "title"
                    }

                    ListView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        boundsBehavior: Flickable.StopAtBounds
                        model: root.sections

                        delegate: ListRow {
                            required property var modelData

                            width: ListView.view.width
                            implicitHeight: 34
                            title: modelData.title
                            glyph: modelData.glyph
                            iconSize: 16
                            selected: root.section === modelData.id
                            onActivated: root.section = modelData.id
                        }
                    }
                }
            }

            Separator { Layout.fillHeight: true; vertical: true }

            // ── Pane ─────────────────────────────────────────────────

            Flickable {
                Layout.fillWidth: true
                Layout.fillHeight: true
                contentHeight: pane.implicitHeight + Theme.spacingXl * 2
                clip: true
                boundsBehavior: Flickable.StopAtBounds

                ColumnLayout {
                    id: pane
                    x: Theme.spacingXl
                    y: Theme.spacingLg
                    width: parent.width - Theme.spacingXl * 2
                    spacing: Theme.spacingLg

                    Label {
                        Layout.fillWidth: true
                        text: root.currentTitle
                        variant: "titleLarge"
                    }

                    Loader {
                        Layout.fillWidth: true
                        // Only the visible section exists: nineteen panes
                        // instantiated at once is a slow window to open
                        // and a lot of bindings nobody is looking at.
                        source: "Sections/" + root.sectionFile + ".qml"
                        asynchronous: true
                    }
                }
            }
        }
    }

    readonly property string currentTitle: {
        const entry = root.sections.find(item => item.id === root.section);
        return entry ? entry.title : "Settings";
    }

    readonly property string sectionFile: {
        switch (root.section) {
        case "appearance": return "AppearanceSection";
        case "glass": return "GlassSection";
        case "wallpaper": return "WallpaperSection";
        case "animations": return "AnimationsSection";
        case "keybinds": return "KeybindsSection";
        case "workspaces": return "WorkspacesSection";
        case "displays": return "DisplaysSection";
        case "audio": return "AudioSection";
        case "network": return "NetworkSection";
        case "bluetooth": return "BluetoothSection";
        case "notifications": return "NotificationsSection";
        case "battery": return "BatterySection";
        case "performance": return "PerformanceSection";
        case "assistant": return "AssistantSection";
        case "hypernix": return "HyperNixSection";
        case "applications": return "ApplicationsSection";
        case "privacy": return "PrivacySection";
        case "accessibility": return "AccessibilitySection";
        default: return "AboutSection";
        }
    }
}
