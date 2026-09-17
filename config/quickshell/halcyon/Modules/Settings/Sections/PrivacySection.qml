import QtQuick
import QtQuick.Layouts
import qs.Config
import qs.Components
import ".."

ColumnLayout {
    spacing: Theme.spacingLg

    SettingsGroup {
        title: "On this machine"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingMd

            SettingRow {
                title: "Clipboard history"
                description: "Stored locally by cliphist and searchable from Spotlight."

                GlassToggle {
                    checked: Config.get("privacy.clipboardHistory", true)
                    onToggled: value => Config.set("privacy.clipboardHistory", value)
                }
            }

            GlassSetting {
                path: "privacy.clipboardHistoryLimit"
                title: "Entries kept"
                from: 20; to: 1000; step: 20; fallback: 200; integer: true
            }

            SettingRow {
                title: "Recent files"
                description: "Offer recently opened files in Spotlight."

                GlassToggle {
                    checked: Config.get("privacy.recentFiles", true)
                    onToggled: value => Config.set("privacy.recentFiles", value)
                }
            }
        }
    }

    SettingsGroup {
        title: "Off this machine"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingMd

            Label {
                Layout.fillWidth: true
                text: "Halcyon has no telemetry and makes no network request you did "
                    + "not ask for. The only outbound traffic it can generate is a "
                    + "web search you run, and the European Central Bank's daily "
                    + "exchange-rate file — both gated on the switch below."
                variant: "caption"
                tone: "tertiary"
                wrapMode: Text.WordWrap
            }

            SettingRow {
                title: "Allow web access"

                GlassToggle {
                    checked: Config.get("assistant.privacy.allowWebAccess", false)
                    onToggled: value => Config.set("assistant.privacy.allowWebAccess", value)
                }
            }
        }
    }
}
