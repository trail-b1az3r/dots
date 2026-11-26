pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import qs.common
import qs.services

// Wi-Fi: on or off, and the networks in range, strongest first after the one in use and the known ones. Click one to
// join (a network that needs a password asks for it here); the one in use disconnects.
Item {
    id: root
    signal back
    property string asking: ""   // the network whose password is being typed

    Component.onCompleted: {
        Network.refresh();
        Network.scan();
    }

    PageHeader {
        id: head
        width: parent.width
        title: "Wi-Fi"
        onBack: root.back()
        BarButton {
            icon: "refresh"
            onClicked: Network.scan()
            RotationAnimation on rotation {
                running: Network.scanning
                loops: Animation.Infinite
                from: 0
                to: 360
                duration: 900
            }
        }
        Switch {
            anchors.verticalCenter: parent.verticalCenter
            checked: Network.enabled
            onToggled: Network.setEnabled(!Network.enabled)
        }
    }

    Text {
        id: error
        anchors.top: head.bottom
        anchors.topMargin: 6
        width: parent.width
        visible: Network.error !== ""
        text: Network.error
        color: "#FF8A80"
        wrapMode: Text.Wrap
        font.family: Theme.font
        font.pixelSize: 12
    }

    ListView {
        id: list
        anchors.top: error.visible ? error.bottom : head.bottom
        anchors.topMargin: 10
        anchors.bottom: settings.top
        anchors.bottomMargin: 8
        width: parent.width
        clip: true
        spacing: 4
        visible: Network.enabled
        model: Network.networks
        delegate: Rectangle {
            id: row
            required property var modelData
            readonly property bool asking: root.asking === modelData.ssid
            width: list.width
            height: asking ? 96 : 48
            Behavior on height { NumberAnimation { duration: Theme.animMs; easing.type: Easing.OutCubic } }
            radius: 14
            clip: true
            color: modelData.active ? Theme.alpha(Theme.accent, 0.2) : rowArea.containsMouse ? Theme.alpha(Theme.text, 0.08) : Theme.alpha(Theme.text, 0.04)

            MouseArea {
                id: rowArea
                width: parent.width
                height: 48
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    if (row.modelData.active)
                        Network.disconnect();
                    else if (row.modelData.secure && !row.modelData.known)
                        root.asking = row.asking ? "" : row.modelData.ssid;
                    else
                        Network.connect(row.modelData.ssid, "");
                }
            }
            Row {
                x: 12
                height: 48
                spacing: 10
                Symbol {
                    anchors.verticalCenter: parent.verticalCenter
                    name: row.modelData.signal > 66 ? "wifi" : row.modelData.signal > 33 ? "wifi_2_bar" : "wifi_1_bar"
                    fill: row.modelData.active ? 1 : 0
                    color: row.modelData.active ? Theme.accent : Theme.text
                }
                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    Text {
                        text: row.modelData.ssid
                        color: Theme.text
                        font.family: Theme.font
                        font.pixelSize: 13
                        font.weight: row.modelData.active ? Font.DemiBold : Font.Normal
                        elide: Text.ElideRight
                        width: list.width - 110
                    }
                    Text {
                        text: Network.connecting === row.modelData.ssid ? "Connecting…"
                            : row.modelData.active ? "Connected · click to disconnect" : row.modelData.known ? "Saved" : row.modelData.secure ? "Secured" : "Open"
                        color: Theme.muted
                        font.family: Theme.font
                        font.pixelSize: 11
                    }
                }
            }
            Symbol {
                anchors.right: parent.right
                anchors.rightMargin: 12
                y: 14
                visible: row.modelData.secure
                name: "lock"
                size: 16
                color: Theme.muted
            }
            // The password, for a secured network not joined before.
            TextField {
                id: password
                visible: row.asking
                x: 12
                y: 52
                width: parent.width - 24
                height: 36
                echoMode: TextInput.Password
                placeholderText: "Password for " + row.modelData.ssid
                placeholderTextColor: Theme.muted
                color: Theme.text
                font.family: Theme.font
                font.pixelSize: 13
                leftPadding: 12
                background: Rectangle { radius: 12; color: Theme.alpha(Theme.text, 0.1) }
                onVisibleChanged: if (visible) forceActiveFocus()
                onAccepted: {
                    Network.connect(row.modelData.ssid, text);
                    text = "";
                    root.asking = "";
                }
            }
        }
    }

    Text {
        anchors.centerIn: list
        visible: !Network.enabled || (Network.networks.length === 0 && !Network.scanning)
        text: !Network.enabled ? "Wi-Fi is off" : "No networks found"
        color: Theme.muted
        font.family: Theme.font
        font.pixelSize: 13
    }

    BarButton {
        id: settings
        anchors.bottom: parent.bottom
        anchors.horizontalCenter: parent.horizontalCenter
        icon: "settings"
        label: "Network settings"
        onClicked: Actions.run("nm-connection-editor || kitty -e nmtui")
    }
}
