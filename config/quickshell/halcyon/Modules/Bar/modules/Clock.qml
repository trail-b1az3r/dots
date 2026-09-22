import QtQuick
import Quickshell
import qs.Config
import qs.Services
import "../"

/**
 * The time, and the calendar behind it.
 *
 * SystemClock ticks at the precision asked for, so a bar showing hours
 * and minutes wakes once a minute rather than once a second. That is
 * the difference between a bar that costs nothing when idle and one
 * that keeps a core warm.
 */
BarItem {
    id: root

    property var hostBar: null

    readonly property bool showSeconds: Config.get("bar.clock.seconds", false)
    readonly property string format: Config.get(
        "bar.clock.format", root.showSeconds ? "HH:mm:ss" : "HH:mm")

    tooltip: Qt.formatDateTime(clock.date, "dddd d MMMM yyyy")
    onActivated: Actions.run(["shell", "calendar", "toggle"])
    onSecondaryActivated: Actions.run(["shell", "dashboard", "toggle"])

    SystemClock {
        id: clock

        precision: root.showSeconds ? SystemClock.Seconds : SystemClock.Minutes
    }

    content: Text {
        text: Qt.formatDateTime(clock.date, root.format)
        color: Theme.text
        font.family: Theme.fontFamily
        font.pixelSize: Theme.sizeBody
        font.features: ({ "tnum": 1 })
        renderType: Text.QtRendering
    }
}
