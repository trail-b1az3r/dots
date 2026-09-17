import QtQuick
import QtQuick.Layouts
import qs.Config
import qs.Components
import qs.Services
import ".."

ColumnLayout {
    spacing: Theme.spacingLg

    SettingsGroup {
        title: "Notifications"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingMd

            SettingRow {
                title: "Do Not Disturb"
                description: "Silences popups. Notifications still reach history, "
                    + "and critical ones are still shown."

                GlassToggle {
                    checked: Notifications.doNotDisturb
                    onToggled: value => Notifications.setDoNotDisturb(value)
                }
            }

            SettingRow {
                title: "Position"

                GlassSegmented {
                    options: [
                        { value: "top-right", title: "Top right" },
                        { value: "top-left", title: "Top left" },
                        { value: "bottom-right", title: "Bottom right" },
                        { value: "bottom-left", title: "Bottom left" }
                    ]
                    value: Config.get("notifications.position", "top-right")
                    onSelected: value => Config.set("notifications.position", value)
                }
            }

            SettingRow {
                title: "Group by application"

                GlassToggle {
                    checked: Config.get("notifications.groupByApp", true)
                    onToggled: value => Config.set("notifications.groupByApp", value)
                }
            }

            GlassSetting {
                path: "notifications.maxVisible"
                title: "Popups at once"
                from: 1; to: 8; step: 1; fallback: 4; integer: true
            }

            GlassSetting {
                path: "notifications.defaultTimeout"
                title: "Timeout"
                from: 2; to: 30; step: 1; fallback: 6; integer: true; suffix: " s"
            }

            GlassSetting {
                path: "notifications.criticalTimeout"
                title: "Critical timeout"
                prose: "0 stays until dismissed."
                from: 0; to: 60; step: 5; fallback: 0; integer: true; suffix: " s"
            }

            GlassSetting {
                path: "notifications.historyLimit"
                title: "History"
                from: 10; to: 500; step: 10; fallback: 120; integer: true
            }
        }
    }
}
