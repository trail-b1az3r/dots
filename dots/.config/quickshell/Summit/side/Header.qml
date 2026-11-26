import QtQuick
import Quickshell
import Quickshell.Io
import qs.common
import qs.services

// The side menu's top row, as the Halcyon shell's: how long the computer has been up, then reload, settings and
// the power menu.
Item {
    id: root
    signal closeRequested
    implicitHeight: 40

    property string uptime: ""
    FileView {
        id: uptimeFile
        path: "/proc/uptime"
        onLoaded: {
            const seconds = parseFloat(text().split(" ")[0]) || 0;
            const d = Math.floor(seconds / 86400), h = Math.floor(seconds % 86400 / 3600), m = Math.floor(seconds % 3600 / 60);
            root.uptime = (d > 0 ? d + " d " : "") + (d > 0 || h > 0 ? h + " h " : "") + m + " min";
        }
    }
    Timer {
        interval: 30000
        running: root.visible
        repeat: true
        triggeredOnStart: true
        onTriggered: uptimeFile.reload()
    }

    Rectangle {
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        height: parent.height
        width: up.implicitWidth + 28
        radius: height / 2
        color: Theme.alpha(Theme.text, 0.08)
        Row {
            id: up
            anchors.centerIn: parent
            spacing: 8
            Symbol {
                name: "landscape"
                fill: 1
                color: Theme.accent
                anchors.verticalCenter: parent.verticalCenter
            }
            Text {
                text: "Up " + root.uptime
                color: Theme.text
                font.family: Theme.font
                font.pixelSize: 13
                font.weight: Font.Medium
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }

    Rectangle {
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        height: parent.height
        width: buttons.implicitWidth + 8
        radius: height / 2
        color: Theme.alpha(Theme.text, 0.08)
        Row {
            id: buttons
            anchors.centerIn: parent
            spacing: 2
            BarButton {
                icon: "restart_alt"
                implicitHeight: 32
                // Hyprland's config and Summit, both read again.
                onClicked: {
                    Quickshell.execDetached(["hyprctl", "reload"]);
                    Quickshell.reload(true);
                }
            }
            BarButton {
                icon: "settings"
                implicitHeight: 32
                onClicked: {
                    root.closeRequested();
                    Actions.settings();
                }
            }
            BarButton {
                icon: "power_settings_new"
                implicitHeight: 32
                onClicked: {
                    root.closeRequested();
                    Actions.power();
                }
            }
        }
    }
}
