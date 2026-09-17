import QtQuick
import QtQuick.Layouts
import qs.Config
import qs.Components
import qs.Services

/** The expanded Bluetooth list: connected, paired, then nearby. */
GlassSurface {
    id: root

    level: 1
    radius: Theme.radiusLg
    padding: Theme.panelPaddingTight
    implicitHeight: Math.min(300, layout.implicitHeight + padding * 2)

    readonly property var sections: [
        { title: "Connected", items: Bt.connectedDevices },
        { title: "Paired", items: Bt.pairedDevices },
        { title: "Nearby", items: Bt.nearbyDevices }
    ].filter(section => section.items.length > 0)

    ColumnLayout {
        id: layout
        anchors.fill: parent
        spacing: Theme.spacingXs

        RowLayout {
            Layout.fillWidth: true

            Label {
                Layout.fillWidth: true
                text: Bt.enabled ? "Devices" : "Bluetooth is off"
                variant: "caption"
                tone: "tertiary"
                font.weight: Theme.weightSemibold
            }

            Spinner {
                size: 12
                visible: Bt.discovering
            }
        }

        Flickable {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredHeight: Math.min(230, column.implicitHeight)
            visible: Bt.enabled
            contentHeight: column.implicitHeight
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            ColumnLayout {
                id: column
                width: parent.width
                spacing: 0

                Repeater {
                    model: root.sections

                    ColumnLayout {
                        required property var modelData
                        Layout.fillWidth: true
                        spacing: 0

                        Label {
                            Layout.fillWidth: true
                            Layout.topMargin: Theme.spacingXs
                            visible: root.sections.length > 1
                            text: modelData.title
                            variant: "caption"
                            tone: "tertiary"
                        }

                        Repeater {
                            model: modelData.items

                            ListRow {
                                required property var modelData

                                Layout.fillWidth: true
                                implicitHeight: 40
                                title: modelData.deviceName.length > 0
                                    ? modelData.deviceName
                                    : modelData.address
                                subtitle: {
                                    if (modelData.connected) {
                                        return modelData.batteryAvailable
                                            ? "Connected · " + Math.round(modelData.battery * 100) + "%"
                                            : "Connected";
                                    }
                                    if (modelData.pairing) return "Pairing…";
                                    return modelData.paired ? "Paired" : "Not paired";
                                }
                                glyph: Bt.deviceGlyph(modelData)
                                iconSize: 18
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
                    }
                }
            }
        }

        Label {
            Layout.fillWidth: true
            Layout.margins: Theme.spacingSm
            visible: Bt.enabled && root.sections.length === 0
            text: Bt.discovering ? "Looking for devices…" : "No devices found"
            variant: "footnote"
            tone: "tertiary"
            horizontalAlignment: Text.AlignHCenter
        }
    }
}
