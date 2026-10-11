import QtQuick
import qs.Config
import qs.Services
import qs.Components
import "../"

/** Opens Halcyon's system summary, with the mark turning, in a terminal. */
BarItem {
    id: root

    property var hostBar: null

    tooltip: qsTr("System summary")
    onActivated: Actions.run(["action", "system.fetch"])

    content: Icon {
        glyph: "󰕒"
        size: Theme.sizeBody
        color: root.hovered ? Theme.text : Theme.textSecondary
    }
}
