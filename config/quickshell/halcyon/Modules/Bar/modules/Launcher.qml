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
        // An absolute path, not a theme name: no icon theme ships a
        // "halcyon" entry, so the old lookup always fell through to the
        // glyph and the mark was never shown. The glyph remains the
        // fallback for a tree that has not been installed.
        source: Paths.logo
        glyph: "\udb81\udf3b"
        size: Theme.sizeBodyLarge
        color: Theme.accent
    }
}
