import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Hyprland
import qs.Config
import qs.Components
import ".."

ColumnLayout {
    spacing: Theme.spacingLg

    SettingsGroup {
        title: "Displays"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingMd

            Repeater {
                model: Hyprland.monitors.values

                ColumnLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    spacing: 1

                    Label {
                        Layout.fillWidth: true
                        text: modelData.name
                            + (modelData.focused ? "  (focused)" : "")
                        variant: "body"
                        font.weight: Theme.weightMedium
                    }

                    Label {
                        Layout.fillWidth: true
                        text: modelData.width + " × " + modelData.height
                            + "  ·  scale " + modelData.scale.toFixed(2)
                            + "  ·  at " + modelData.x + ", " + modelData.y
                        variant: "caption"
                        tone: "tertiary"
                    }

                    Label {
                        Layout.fillWidth: true
                        visible: modelData.description.length > 0
                        text: modelData.description
                        variant: "caption"
                        tone: "tertiary"
                        elide: Text.ElideRight
                    }
                }
            }

            Label {
                Layout.fillWidth: true
                visible: Hyprland.monitors.values.length === 0
                text: "No displays reported — Hyprland may not be running."
                variant: "footnote"
                tone: "tertiary"
            }
        }
    }

    SettingsGroup {
        title: "Behaviour"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingMd

            SettingRow {
                title: "Variable refresh rate"
                description: "0 off, 1 on, 2 only for fullscreen, 3 only for "
                    + "fullscreen video."

                GlassSegmented {
                    options: [
                        { value: "0", title: "Off" },
                        { value: "1", title: "On" },
                        { value: "2", title: "Fullscreen" },
                        { value: "3", title: "Video" }
                    ]
                    value: String(Config.get("displays.vrr", 1))
                    onSelected: value => Config.set("displays.vrr", parseInt(value, 10))
                }
            }

            SettingRow {
                title: "Allow tearing"
                description: "Lets a fullscreen game present without waiting for "
                    + "vblank. Lower latency, visible tearing."

                GlassToggle {
                    checked: Config.get("displays.allowTearing", false)
                    onToggled: value => Config.set("displays.allowTearing", value)
                }
            }

            SettingRow {
                title: "Default scale"
                description: "\"auto\" lets Hyprland choose, or give a number such "
                    + "as 1.25 for fractional scaling."

                GlassField {
                    implicitWidth: 120
                    implicitHeight: 30
                    text: String(Config.get("displays.defaultScale", "auto"))
                    onAccepted: value => Config.set("displays.defaultScale", value)
                }
            }
        }
    }

    SettingsGroup {
        title: "Per-display configuration"

        Label {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            text: "Resolution, position and rotation are set per display in "
                + "settings.json under displays.monitors, using the same fields "
                + "Hyprland's hl.monitor() takes: output, mode, position, scale, "
                + "transform. Halcyon regenerates the compositor's configuration "
                + "from that list."
            variant: "footnote"
            tone: "secondary"
            wrapMode: Text.WordWrap
        }
    }
}
