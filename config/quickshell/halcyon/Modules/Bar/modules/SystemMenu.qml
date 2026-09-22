import QtQuick
import qs.Config
import qs.Services
import qs.Components
import "../"

/** Control Center on click, the power menu on right-click. */
BarItem {
    id: root

    property var hostBar: null

    tooltip: qsTr("Control Center · right-click for power")
    onActivated: Actions.run(["shell", "control", "toggle"])
    onSecondaryActivated: Actions.run(["shell", "power", "toggle"])

    content: Icon {
        glyph: "\udb85\udcc6"
        size: Theme.sizeBody
        color: Theme.textSecondary
    }
}
