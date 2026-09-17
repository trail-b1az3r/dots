import QtQuick
import QtQuick.Layouts
import qs.Config
import qs.Components
import qs.Services
import ".."

ColumnLayout {
    id: root
    spacing: Theme.spacingLg

    Component.onCompleted: Net.scanning = true
    Component.onDestruction: Net.scanning = false

    SettingsGroup {
        title: "Wi-Fi"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingMd

            SettingRow {
                title: "Wi-Fi"
                description: Net.summary

                GlassToggle {
                    checked: Net.wifiEnabled
                    enabled: Net.wifiHardwareEnabled
                    onToggled: value => Net.setWifiEnabled(value)
                }
            }

            Label {
                Layout.fillWidth: true
                visible: !Net.wifiHardwareEnabled
                text: "The Wi-Fi radio is blocked in hardware — check the switch or "
                    + "function key on this machine."
                variant: "caption"
                color: Theme.warning
                wrapMode: Text.WordWrap
            }

            Repeater {
                model: Net.wifiEnabled ? Net.networks.slice(0, 12) : []

                ListRow {
                    required property var modelData
                    Layout.fillWidth: true
                    implicitHeight: 38
                    title: modelData.name
                    subtitle: modelData.connected
                        ? "Connected"
                        : Net.securityLabel(modelData)
                            + " · " + Math.round(modelData.signalStrength) + "%"
                    glyph: modelData.signalStrength >= 60 ? "󰤨" : "󰤟"
                    iconSize: 16
                    selected: modelData.connected
                    onActivated: {
                        if (modelData.connected)
                            Net.disconnect();
                        else
                            Net.connect(modelData, "");
                    }
                }
            }
        }
    }

    SettingsGroup {
        title: "Wired"
        visible: Net.wiredDevice !== null

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: 1

            Label {
                Layout.fillWidth: true
                text: Net.wiredDevice ? Net.wiredDevice.name : ""
                variant: "body"
            }

            Label {
                Layout.fillWidth: true
                text: Net.wiredConnected
                    ? (Net.wiredDevice?.address ?? "Connected")
                    : "Not connected"
                variant: "caption"
                tone: "tertiary"
            }
        }
    }

    SettingsGroup {
        title: "Search"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingMd

            SettingRow {
                title: "Search engine"
                description: "{query} is replaced with what you typed."

                GlassField {
                    implicitWidth: 260
                    implicitHeight: 30
                    text: Config.get("search.webSearchUrl", "")
                    onAccepted: value => Config.set("search.webSearchUrl", value)
                }
            }

            SettingRow {
                title: "Name"

                GlassField {
                    implicitWidth: 160
                    implicitHeight: 30
                    text: Config.get("search.webSearchName", "DuckDuckGo")
                    onAccepted: value => Config.set("search.webSearchName", value)
                }
            }
        }
    }
}
