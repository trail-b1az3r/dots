import QtQuick
import QtQuick.Layouts
import qs.Config
import qs.Components
import qs.Services

/** The expanded Wi-Fi list, with an inline password prompt. */
GlassSurface {
    id: root

    level: 1
    radius: Theme.radiusLg
    padding: Theme.panelPaddingTight
    implicitHeight: Math.min(300, layout.implicitHeight + padding * 2)

    property var pendingNetwork: null

    ColumnLayout {
        id: layout
        anchors.fill: parent
        spacing: Theme.spacingXs

        RowLayout {
            Layout.fillWidth: true

            Label {
                Layout.fillWidth: true
                text: Net.wifiEnabled ? "Networks" : "Wi-Fi is off"
                variant: "caption"
                tone: "tertiary"
                font.weight: Theme.weightSemibold
            }

            Spinner {
                size: 12
                visible: Net.scanning && Net.networks.length === 0
            }
        }

        ListView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredHeight: Math.min(220, contentHeight)
            visible: Net.wifiEnabled
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            model: Net.networks

            delegate: ListRow {
                required property var modelData

                width: ListView.view.width
                implicitHeight: 40
                title: modelData.name
                subtitle: modelData.connected
                    ? "Connected"
                    : Net.securityLabel(modelData) + " · " + Math.round(modelData.signalStrength) + "%"
                glyph: {
                    const strength = modelData.signalStrength;
                    if (strength >= 75) return "󰤨";
                    if (strength >= 50) return "󰤥";
                    if (strength >= 25) return "󰤢";
                    return "󰤟";
                }
                iconSize: 18
                selected: modelData.connected

                onActivated: {
                    if (modelData.connected) {
                        Net.disconnect();
                        return;
                    }
                    if (modelData.known || Net.securityLabel(modelData) === "Open") {
                        Net.connect(modelData, "");
                        return;
                    }
                    // A network we have no secret for needs one, and the
                    // prompt belongs here rather than in a separate dialog.
                    root.pendingNetwork = modelData;
                    password.text = "";
                    password.forceActiveFocus();
                }

                onRightClicked: {
                    if (modelData.known)
                        Net.forget(modelData);
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            visible: root.pendingNetwork !== null
            spacing: Theme.spacingXs

            GlassField {
                id: password
                Layout.fillWidth: true
                implicitHeight: 32
                glyph: "󰌾"
                placeholder: root.pendingNetwork
                    ? "Password for " + root.pendingNetwork.name
                    : "Password"
                echoMode: TextInput.Password
                onAccepted: text => {
                    Net.connect(root.pendingNetwork, text);
                    root.pendingNetwork = null;
                }
                onEscaped: root.pendingNetwork = null
            }

            GlassIconButton {
                glyph: "󰅖"
                size: 28
                iconSize: 12
                tooltip: "Cancel"
                onClicked: root.pendingNetwork = null
            }
        }
    }
}
