import QtQuick
import QtQuick.Layouts
import qs.Config
import qs.Components
import ".."

ColumnLayout {
    spacing: Theme.spacingLg

    SettingsGroup {
        title: "Defaults"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingMd

            Label {
                Layout.fillWidth: true
                text: "Used by the shortcuts and by the assistant. Leave blank to "
                    + "fall back to whatever is installed."
                variant: "caption"
                tone: "tertiary"
                wrapMode: Text.WordWrap
            }

            Repeater {
                model: [
                    { path: "applications.terminal", title: "Terminal", hint: "kitty" },
                    { path: "applications.browser", title: "Browser", hint: "firefox" },
                    { path: "applications.fileManager", title: "File manager", hint: "nautilus" },
                    { path: "applications.editor", title: "Editor", hint: "code" }
                ]

                SettingRow {
                    required property var modelData
                    title: modelData.title

                    GlassField {
                        implicitWidth: 220
                        implicitHeight: 30
                        placeholder: modelData.hint
                        text: Config.get(modelData.path, "")
                        onAccepted: value => Config.set(modelData.path, value)
                    }
                }
            }
        }
    }

    SettingsGroup {
        title: "Capture"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingMd

            SettingRow {
                title: "Screenshots"

                GlassField {
                    implicitWidth: 240
                    implicitHeight: 30
                    text: Config.get("applications.screenshotDir", "~/Pictures/Screenshots")
                    onAccepted: value => Config.set("applications.screenshotDir", value)
                }
            }

            SettingRow {
                title: "Recordings"

                GlassField {
                    implicitWidth: 240
                    implicitHeight: 30
                    text: Config.get("applications.recordingDir", "~/Videos/Recordings")
                    onAccepted: value => Config.set("applications.recordingDir", value)
                }
            }
        }
    }
}
