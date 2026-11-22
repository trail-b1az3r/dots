import QtQuick
import Quickshell
import qs.common

// The date and time, centred in the top bar. Click for the calendar.
BarButton {
    id: root
    property alias date: clock.date
    signal toggled
    label: Qt.formatDateTime(clock.date, "ddd d MMM") + "   " + Qt.formatDateTime(clock.date, "HH:mm")
    onClicked: root.toggled()

    SystemClock {
        id: clock
        precision: SystemClock.Minutes
    }
}
