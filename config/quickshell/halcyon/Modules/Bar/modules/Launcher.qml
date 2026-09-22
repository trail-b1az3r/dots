import QtQuick
import qs.Config
import qs.Services
import qs.Components
import "../"

/** The Halcyon mark; opens Spotlight, right-click for the power menu. */
BarItem {
    id: root

    property var hostBar: null

    tooltip: qsTr("Search · right-click for power")
    onActivated: Actions.run(["shell", "spotlight", "toggle"])
    onSecondaryActivated: Actions.run(["shell", "power", "toggle"])

    content: Icon {
        source: "halcyon"
        glyph: "\udb81\udf3b"
        size: Theme.sizeBodyLarge
        color: Theme.accent
    }
}
