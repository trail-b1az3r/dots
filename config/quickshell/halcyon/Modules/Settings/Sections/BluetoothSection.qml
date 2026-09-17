import QtQuick
import QtQuick.Layouts
import qs.Config
import qs.Components
import qs.Services
import ".."

ColumnLayout {
    spacing: Theme.spacingLg

    Component.onCompleted: Bt.scanning = true
    Component.onDestruction: Bt.scanning = false

    SettingsGroup {
        title: "Bluetooth"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingMd

            SettingRow {
                title: "Bluetooth"
                description: Bt.available ? Bt.summary : "No adapter found"

                GlassToggle {
                    checked: Bt.enabled
                    enabled: Bt.available
                    onToggled: value => Bt.setEnabled(value)
                }
            }

            SettingRow {
                title: "Discoverable"
                description: "Lets other devices find this one while the panel is open."
                visible: Bt.available && Bt.enabled

                GlassToggle {
                    checked: Bt.adapter?.discoverable ?? false
                    onToggled: value => {
                        if (Bt.adapter)
                            Bt.adapter.discoverable = value;
                    }
                }
            }

            Repeater {
                model: Bt.enabled ? Bt.devices : []

                ListRow {
                    required property var modelData
                    Layout.fillWidth: true
                    implicitHeight: 40
                    title: modelData.deviceName.length > 0
                        ? modelData.deviceName : modelData.address
                    subtitle: {
                        if (modelData.connected) {
                            return modelData.batteryAvailable
                                ? "Connected · battery " + Math.round(modelData.battery * 100) + "%"
                                : "Connected";
                        }
                        if (modelData.pairing) return "Pairing…";
                        return modelData.paired ? "Paired" : "Not paired";
                    }
                    glyph: Bt.deviceGlyph(modelData)
                    iconSize: 17
                    selected: modelData.connected
                    onActivated: {
                        if (modelData.connected)
                            Bt.disconnectDevice(modelData);
                        else
                            Bt.connectDevice(modelData);
                    }
                    onRightClicked: {
                        if (modelData.paired)
                            Bt.forgetDevice(modelData);
                    }
                }
            }

            Label {
                Layout.fillWidth: true
                visible: Bt.enabled && Bt.devices.length === 0
                text: Bt.discovering ? "Looking for devices…" : "No devices"
                variant: "footnote"
                tone: "tertiary"
            }
        }
    }
}
