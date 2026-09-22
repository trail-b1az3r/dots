import QtQuick
import Quickshell
import qs.Config
import qs.Services
import "../"

/** The date, for people who want it separate from the time. */
BarItem {
    id: root

    property var hostBar: null

    readonly property string format: Config.get("bar.date.format", "ddd d MMM")

    tooltip: Qt.formatDateTime(clock.date, "dddd d MMMM yyyy")
    onActivated: Actions.run(["shell", "calendar", "toggle"])

    SystemClock {
        id: clock

        precision: SystemClock.Minutes
    }

    content: Text {
        text: Qt.formatDateTime(clock.date, root.format)
        color: Theme.textSecondary
        font.family: Theme.fontFamily
        font.pixelSize: Theme.sizeFootnote
        renderType: Text.QtRendering
    }
}
