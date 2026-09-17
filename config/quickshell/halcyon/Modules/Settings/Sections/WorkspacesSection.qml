import QtQuick
import QtQuick.Layouts
import qs.Config
import qs.Components
import qs.Services
import ".."

ColumnLayout {
    spacing: Theme.spacingLg

    SettingsGroup {
        title: "Spaces"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingMd

            GlassSetting {
                path: "workspaces.count"
                title: "Number of workspaces"
                from: 1; to: 20; step: 1; fallback: 10; integer: true
            }

            SettingRow {
                title: "Persistent"
                description: "Workspaces exist before you visit them, so the "
                    + "indicator does not change width as you move around."

                GlassToggle {
                    checked: Config.get("workspaces.persistent", true)
                    onToggled: value => Config.set("workspaces.persistent", value)
                }
            }

            SettingRow {
                title: "Per monitor"
                description: "Each display keeps its own current workspace."

                GlassToggle {
                    checked: Config.get("workspaces.perMonitor", true)
                    onToggled: value => Config.set("workspaces.perMonitor", value)
                }
            }

            SettingRow {
                title: "Smart gaps"
                description: "Remove gaps and rounding when a workspace holds one "
                    + "tiled window."

                GlassToggle {
                    checked: Config.get("workspaces.smartGaps", true)
                    onToggled: value => Config.set("workspaces.smartGaps", value)
                }
            }
        }
    }

    SettingsGroup {
        title: "Names"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingSm

            Label {
                Layout.fillWidth: true
                text: "A name replaces the number in the indicator and the overview."
                variant: "caption"
                tone: "tertiary"
            }

            Repeater {
                model: Workspaces.count

                RowLayout {
                    required property int index
                    Layout.fillWidth: true
                    spacing: Theme.spacingMd

                    Label {
                        Layout.preferredWidth: 30
                        text: String(index + 1)
                        variant: "footnote"
                        tone: "tertiary"
                    }

                    GlassField {
                        Layout.fillWidth: true
                        implicitHeight: 28
                        placeholder: "Workspace " + (index + 1)
                        text: Config.get("workspaces.names", ({}))[String(index + 1)] ?? ""
                        onAccepted: value => {
                            const names = Object.assign({}, Config.get("workspaces.names", ({})));
                            if (value.trim().length === 0)
                                delete names[String(index + 1)];
                            else
                                names[String(index + 1)] = value;
                            Config.set("workspaces.names", names);
                        }
                    }
                }
            }
        }
    }
}
