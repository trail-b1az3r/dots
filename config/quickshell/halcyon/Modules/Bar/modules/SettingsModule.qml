import QtQuick
import qs.Config
import qs.Services
import qs.Components
import "../"

/** Opens Halcyon settings. */
BarItem {
    id: root

    property var hostBar: null

    tooltip: qsTr("Settings")
    onActivated: Actions.run(["shell", "settings", "toggle"])

    content: Icon {
        glyph: "\udb80\udf93"
        size: Theme.sizeBody
        color: Theme.textSecondary
    }
}
