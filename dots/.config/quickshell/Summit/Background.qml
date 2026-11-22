import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.common

// The wallpaper, on the background layer of every screen; a quiet gradient until a theme sets one.
PanelWindow {
    required property var modelData
    screen: modelData
    WlrLayershell.layer: WlrLayer.Background
    WlrLayershell.namespace: "summit-wallpaper"
    exclusionMode: ExclusionMode.Ignore
    anchors { top: true; bottom: true; left: true; right: true }
    color: Theme.background

    Rectangle {
        anchors.fill: parent
        visible: wall.status !== Image.Ready
        gradient: Gradient {
            GradientStop { position: 0; color: Qt.lighter(Theme.background, 1.6) }
            GradientStop { position: 1; color: Theme.background }
        }
    }
    Image {
        id: wall
        anchors.fill: parent
        source: Theme.wallpaper !== "" ? "file://" + Theme.wallpaper : ""
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        sourceSize: Qt.size(parent.width, parent.height)
        opacity: status === Image.Ready ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: 400 } }
    }
}
