pragma ComponentBehavior: Bound

import QtQuick
import Quickshell.Bluetooth
import qs.common

// Bluetooth: on or off, and the devices: connected first, then paired, then the ones nearby (searched for while
// the page is open). Click to connect or disconnect; a new one pairs first.
Item {
    id: root
    signal back
    readonly property var adapter: Bluetooth.defaultAdapter
    readonly property var devices: (adapter?.devices?.values ?? [])
        .filter(d => d.name && d.name !== d.address?.replace(/:/g, "-"))
        .sort((a, b) => (b.connected - a.connected) || (b.paired - a.paired) || a.name.localeCompare(b.name))

    Component.onCompleted: if (adapter?.enabled) adapter.discovering = true
    Component.onDestruction: if (adapter) adapter.discovering = false

    PageHeader {
        id: head
        width: parent.width
        title: "Bluetooth"
        onBack: root.back()
        Switch {
            anchors.verticalCenter: parent.verticalCenter
            checked: root.adapter?.enabled ?? false
            onToggled: {
                if (!root.adapter)
                    return;
                root.adapter.enabled = !root.adapter.enabled;
                if (root.adapter.enabled)
                    root.adapter.discovering = true;
            }
        }
    }

    ListView {
        id: list
        anchors.top: head.bottom
        anchors.topMargin: 10
        anchors.bottom: parent.bottom
        width: parent.width
        clip: true
        spacing: 4
        visible: root.adapter?.enabled ?? false
        model: root.devices
        delegate: Rectangle {
            id: row
            required property var modelData
            readonly property bool busy: modelData.state === BluetoothDeviceState.Connecting || modelData.state === BluetoothDeviceState.Disconnecting || modelData.pairing
            width: list.width
            height: 52
            radius: 14
            color: modelData.connected ? Theme.alpha(Theme.accent, 0.2) : rowArea.containsMouse ? Theme.alpha(Theme.text, 0.08) : Theme.alpha(Theme.text, 0.04)
            MouseArea {
                id: rowArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    const d = row.modelData;
                    if (d.connected)
                        d.disconnect();
                    else if (!d.paired)
                        d.pair();
                    else
                        d.connect();
                }
            }
            Row {
                x: 12
                anchors.verticalCenter: parent.verticalCenter
                spacing: 10
                Symbol {
                    anchors.verticalCenter: parent.verticalCenter
                    name: /audio|headset|headphone/.test(row.modelData.icon) ? "headphones"
                        : /keyboard/.test(row.modelData.icon) ? "keyboard"
                        : /mouse/.test(row.modelData.icon) ? "mouse"
                        : /phone/.test(row.modelData.icon) ? "mobile" : "bluetooth"
                    fill: row.modelData.connected ? 1 : 0
                    color: row.modelData.connected ? Theme.accent : Theme.text
                }
                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    Text {
                        text: row.modelData.name
                        color: Theme.text
                        font.family: Theme.font
                        font.pixelSize: 13
                        font.weight: row.modelData.connected ? Font.DemiBold : Font.Normal
                        elide: Text.ElideRight
                        width: list.width - 70
                    }
                    Text {
                        text: row.busy ? "Working…" : row.modelData.connected
                            ? "Connected" + (row.modelData.batteryAvailable ? " · " + Math.round(row.modelData.battery * 100) + "%" : "")
                            : row.modelData.paired ? "Paired" : "Nearby · click to pair"
                        color: Theme.muted
                        font.family: Theme.font
                        font.pixelSize: 11
                    }
                }
            }
        }
    }

    Text {
        anchors.centerIn: list
        visible: !(root.adapter?.enabled ?? false) || root.devices.length === 0
        text: !root.adapter ? "No Bluetooth adapter" : !root.adapter.enabled ? "Bluetooth is off" : "Searching…"
        color: Theme.muted
        font.family: Theme.font
        font.pixelSize: 13
    }
}
