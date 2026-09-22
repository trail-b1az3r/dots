import QtQuick
import Quickshell.Hyprland
import qs.Config
import qs.Services
import qs.Components
import "../"

/**
 * The focused window, on this monitor.
 *
 * Elides rather than growing: a bar module that takes the width it
 * wants pushes everything else around every time you focus a terminal
 * with a long path in its title.
 */
BarItem {
    id: root

    property var hostBar: null

    readonly property var focused: Hyprland.activeToplevel
    readonly property string appName: root.focused?.lastIpcObject?.class ?? ""
    readonly property string windowTitle: root.focused?.title ?? ""

    readonly property int maximumWidth: Config.get("bar.activeWindow.maxWidth", 320)

    visible: root.windowTitle !== "" || root.appName !== ""
    tooltip: root.windowTitle
    interactive: false

    content: Row {
        spacing: Theme.spacingXs

        Icon {
            anchors.verticalCenter: parent.verticalCenter
            source: root.appName.toLowerCase()
            glyph: "\udb80\udd3b"
            size: Theme.sizeBody
            color: Theme.textSecondary
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: root.windowTitle || root.appName
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeFootnote
            elide: Text.ElideRight
            width: Math.min(implicitWidth, root.maximumWidth)
            renderType: Text.QtRendering
        }
    }
}
