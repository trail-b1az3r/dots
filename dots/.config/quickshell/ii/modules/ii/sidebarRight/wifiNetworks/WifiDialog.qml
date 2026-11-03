import qs
import qs.services
import qs.services.network
import qs.modules.common
import qs.modules.common.widgets
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io

WindowDialog {
    id: root
    backgroundHeight: 600

    property bool showingDetails: false
    property string detailsOutput: Translation.tr("Loading connection details…")

    Process {
        id: detailsProcess
        // nmxcli (nmx) or nmcli (NetworkManager): the same command, the same output.
        command: [Network.cli, "-f", "GENERAL,IP4,IP6", "device", "show"]
        stdout: StdioCollector {
            onStreamFinished: {
                root.detailsOutput = text.trim().length
                    ? text
                    : (Network.usingNmx ? Translation.tr("nmx returned no connection details.")
                                        : Translation.tr("NetworkManager returned no connection details."))
            }
        }
        onExited: (exitCode, exitStatus) => {
            if (exitCode !== 0 && root.detailsOutput === Translation.tr("Loading connection details…"))
                root.detailsOutput = Network.usingNmx
                    ? Translation.tr("Could not read network details. Check that nmx is running (nmxcli general).")
                    : Translation.tr("Could not read network details. Check that NetworkManager is running.")
        }
    }

    WindowDialogTitle {
        text: root.showingDetails
            ? Translation.tr("Network details")
            : Translation.tr("Connect to Wi-Fi")
    }

    WindowDialogSeparator {
        visible: !root.showingDetails && !Network.wifiScanning
    }

    StyledIndeterminateProgressBar {
        visible: !root.showingDetails && Network.wifiScanning
        Layout.fillWidth: true
        Layout.topMargin: -8
        Layout.bottomMargin: -8
        Layout.leftMargin: -Appearance.rounding.large
        Layout.rightMargin: -Appearance.rounding.large
    }

    ListView {
        visible: !root.showingDetails
        Layout.fillHeight: true
        Layout.fillWidth: true
        Layout.topMargin: -15
        Layout.bottomMargin: -16
        Layout.leftMargin: -Appearance.rounding.large
        Layout.rightMargin: -Appearance.rounding.large

        clip: true
        spacing: 0

        model: ScriptModel {
            values: Network.friendlyWifiNetworks
        }
        delegate: WifiNetworkItem {
            required property WifiAccessPoint modelData
            wifiNetwork: modelData
            width: ListView.view.width
        }
    }

    // Use QtQuick's Flickable instead of QtQuick.Controls.ScrollView.
    // This avoids depending on the Controls ScrollView plugin at runtime.
    Flickable {
        id: detailsFlickable
        visible: root.showingDetails
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.topMargin: -8
        Layout.bottomMargin: -8
        clip: true
        contentWidth: Math.max(width, detailsText.implicitWidth)
        contentHeight: detailsText.implicitHeight

        TextEdit {
            id: detailsText
            width: Math.max(detailsFlickable.width, implicitWidth)
            text: root.detailsOutput
            readOnly: true
            selectByMouse: true
            wrapMode: TextEdit.NoWrap
            color: Appearance.colors.colOnSurface
            font.family: "monospace"
            font.pixelSize: 12
        }
    }

    WindowDialogSeparator {}

    WindowDialogButtonRow {
        DialogButton {
            buttonText: root.showingDetails
                ? Translation.tr("Back")
                : Translation.tr("Details")
            onClicked: {
                if (root.showingDetails) {
                    root.showingDetails = false;
                } else {
                    root.showingDetails = true;
                    root.detailsOutput = Translation.tr("Loading connection details…");
                    detailsProcess.running = true;
                }
            }
        }

        Item {
            Layout.fillWidth: true
        }

        DialogButton {
            buttonText: Translation.tr("Done")
            onClicked: root.dismiss()
        }
    }
}
