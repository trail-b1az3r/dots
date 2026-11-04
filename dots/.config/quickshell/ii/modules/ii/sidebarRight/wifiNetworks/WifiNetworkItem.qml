import qs
import qs.modules.common
import qs.modules.common.widgets
import qs.services
import qs.services.network
import QtQuick
import QtQuick.Layouts

DialogListItem {
    id: root
    required property WifiAccessPoint wifiNetwork
    enabled: !(Network.wifiConnectTarget === root.wifiNetwork && !wifiNetwork?.active)

    active: (wifiNetwork?.askingPassword || wifiNetwork?.active) ?? false
    onClicked: {
        Network.connectToWifiNetwork(wifiNetwork);
    }

    contentItem: ColumnLayout {
        anchors {
            fill: parent
            topMargin: root.verticalPadding
            bottomMargin: root.verticalPadding
            leftMargin: root.horizontalPadding
            rightMargin: root.horizontalPadding
        }
        spacing: 0

        RowLayout {
            // Name
            spacing: 10
            MaterialSymbol {
                iconSize: Appearance.font.pixelSize.larger
                property int strength: root.wifiNetwork?.strength ?? 0
                text: strength > 80 ? "signal_wifi_4_bar" : strength > 60 ? "network_wifi_3_bar" : strength > 40 ? "network_wifi_2_bar" : strength > 20 ? "network_wifi_1_bar" : "signal_wifi_0_bar"
                color: Appearance.colors.colOnSurfaceVariant
            }
            StyledText {
                Layout.fillWidth: true
                color: Appearance.colors.colOnSurfaceVariant
                elide: Text.ElideRight
                text: root.wifiNetwork?.ssid ?? Translation.tr("Unknown")
                textFormat: Text.PlainText
            }
            MaterialSymbol {
                visible: (root.wifiNetwork?.isSecure || root.wifiNetwork?.active) ?? false
                text: root.wifiNetwork?.active ? "check" : Network.wifiConnectTarget === root.wifiNetwork ? "settings_ethernet" : "lock"
                iconSize: Appearance.font.pixelSize.larger
                color: Appearance.colors.colOnSurfaceVariant
            }
        }

        ColumnLayout { // Password
            id: passwordPrompt
            Layout.topMargin: 8
            visible: root.wifiNetwork?.askingPassword ?? false

            // Enterprise (802.1X) networks ask for a username too.
            MaterialTextField {
                id: usernameField
                Layout.fillWidth: true
                visible: root.wifiNetwork?.isEnterprise ?? false
                placeholderText: Translation.tr("Username")
                inputMethodHints: Qt.ImhNoAutoUppercase | Qt.ImhNoPredictiveText
                onAccepted: passwordField.forceActiveFocus()
            }

            MaterialTextField {
                id: passwordField
                Layout.fillWidth: true
                placeholderText: Translation.tr("Password")

                // Password
                echoMode: TextInput.Password
                inputMethodHints: Qt.ImhSensitiveData

                onAccepted: {
                    Network.changePassword(root.wifiNetwork, passwordField.text, usernameField.text);
                }
            }

            RowLayout {
                Layout.fillWidth: true

                Item {
                    Layout.fillWidth: true
                }

                DialogButton {
                    buttonText: Translation.tr("Cancel")
                    onClicked: {
                        root.wifiNetwork.askingPassword = false;
                    }
                }

                DialogButton {
                    buttonText: Translation.tr("Connect")
                    onClicked: {
                        Network.changePassword(root.wifiNetwork, passwordField.text, usernameField.text);
                    }
                }
            }
        }

        StyledText { // Why the last attempt failed, when a password would not fix it
            Layout.topMargin: 6
            Layout.fillWidth: true
            visible: (root.wifiNetwork?.lastError ?? "").length > 0 && !(root.wifiNetwork?.askingPassword ?? false)
            text: root.wifiNetwork?.lastError ?? ""
            wrapMode: Text.Wrap
            font.pixelSize: Appearance.font.pixelSize.smaller
            color: Appearance.colors.colError
        }

        ColumnLayout { // Public wifi login page
            id: publicWifiPortal
            Layout.topMargin: 8
            // An open network, or any network that is holding us at a captive portal
            visible: (root.wifiNetwork?.active && (Network.connectivity === "portal"
                || (root.wifiNetwork?.security ?? "").trim().length === 0)) ?? false

            RowLayout {
                DialogButton {
                    Layout.fillWidth: true
                    buttonText: Network.connectivity === "portal" ? Translation.tr("Sign in to this network")
                                                                   : Translation.tr("Open network portal")
                    colBackground: Appearance.colors.colLayer4
                    colBackgroundHover: Appearance.colors.colLayer4Hover
                    colRipple: Appearance.colors.colLayer4Active
                    onClicked: {
                        Network.openPublicWifiPortal()
                        GlobalStates.sidebarRightOpen = false
                    }
                }
            }
        }

        Item {
            Layout.fillHeight: true
        }
    }
}
