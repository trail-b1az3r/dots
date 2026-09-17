import QtQuick
import QtQuick.Layouts
import qs.Config
import qs.Components
import qs.Services
import ".."

ColumnLayout {
    spacing: Theme.spacingLg

    Component.onCompleted: HyperNix.refresh()

    SettingsGroup {
        title: "Integration"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingMd

            Label {
                Layout.fillWidth: true
                text: "HyperNix is a separate project. Halcyon only reads what its "
                    + "CLI reports and offers to open it — it never starts a training "
                    + "or quantisation run on its own. Turning this off removes every "
                    + "trace of it from the desktop."
                variant: "caption"
                tone: "tertiary"
                wrapMode: Text.WordWrap
            }

            SettingRow {
                title: "Enabled"

                GlassToggle {
                    checked: Config.get("hypernix.enabled", true)
                    onToggled: value => Config.set("hypernix.enabled", value)
                }
            }

            SettingRow {
                title: "Show the widget"
                description: "In Control Center and on the desktop."

                GlassToggle {
                    checked: Config.get("hypernix.showWidget", true)
                    onToggled: value => Config.set("hypernix.showWidget", value)
                }
            }

            SettingRow {
                title: "Show in Spotlight"

                GlassToggle {
                    checked: Config.get("hypernix.showInSpotlight", true)
                    onToggled: value => Config.set("hypernix.showInSpotlight", value)
                }
            }

            GlassSetting {
                path: "hypernix.pollSeconds"
                title: "Refresh interval"
                prose: "How often the widget re-reads HyperNix's device list."
                from: 30; to: 600; step: 30; fallback: 60; integer: true; suffix: " s"
            }

            SettingRow {
                title: "Command"
                description: "Override if hypernix is not on PATH under that name."

                GlassField {
                    implicitWidth: 200
                    implicitHeight: 30
                    text: Config.get("hypernix.command", "hypernix")
                    onAccepted: value => Config.set("hypernix.command", value)
                }
            }
        }
    }

    SettingsGroup {
        title: "Status"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingSm

            Label {
                Layout.fillWidth: true
                text: HyperNix.installed
                    ? "HyperNix " + HyperNix.version
                    : "Not installed"
                variant: "body"
            }

            Label {
                Layout.fillWidth: true
                text: HyperNix.installed
                    ? HyperNix.summary
                    : "Install it with: pip install hypernix"
                variant: "footnote"
                tone: "secondary"
                wrapMode: Text.WordWrap
            }

            Label {
                Layout.fillWidth: true
                visible: HyperNix.devices.length > 0
                text: "Accelerators: " + HyperNix.devices.join(", ")
                variant: "caption"
                tone: "tertiary"
                wrapMode: Text.WordWrap
            }

            RowLayout {
                spacing: Theme.spacingSm

                GlassButton {
                    text: "Refresh"
                    glyph: "󰑐"
                    onClicked: HyperNix.refresh()
                }

                GlassButton {
                    text: "Open HyperNix"
                    glyph: "󰆍"
                    variant: "filled"
                    enabled: HyperNix.available
                    onClicked: HyperNix.launch()
                }
            }
        }
    }
}
