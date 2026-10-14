import qs.services
import qs.modules.common
import qs.modules.common.widgets
import "calendar_layout.js" as CalendarLayout
import QtQuick
import QtQuick.Layouts

Item {
    id: root
    // Layout.topMargin: 10
    anchors.topMargin: 10
    property int monthShift: 0
    // The day the event panel is open at ("YYYY-MM-DD"), or "" when it is closed.
    property string panelDay: ""
    property var viewingDate: CalendarLayout.getDateInXMonthsTime(monthShift)
    property var calendarLayout: CalendarLayout.getCalendarLayout(viewingDate, monthShift === 0)
    width: calendarColumn.width
    implicitHeight: calendarColumn.height + 10 * 2

    // The date of a cell: a cell from the month before or after (greyed out) is in that month.
    function dayKey(row, col) {
        const cell = calendarLayout[row][col];
        let month = viewingDate.getMonth();
        if (cell.today === -1)
            month += row < 2 ? -1 : 1;
        return CalendarEvents.dateKey(new Date(viewingDate.getFullYear(), month, cell.day));
    }

    // The + button: the day being looked at, or the first of the month when looking at another month.
    function newEventDay() {
        if (monthShift === 0)
            return CalendarEvents.dateKey(new Date());
        return CalendarEvents.dateKey(new Date(viewingDate.getFullYear(), viewingDate.getMonth(), 1));
    }

    // Opens the panel on a day and shows its month.
    function openDay(key) {
        const date = CalendarEvents.parseKey(key);
        if (!date)
            return;
        const today = new Date();
        monthShift = (date.getFullYear() - today.getFullYear()) * 12 + date.getMonth() - today.getMonth();
        panelDay = key;
    }

    // The bar's next event was clicked: open on its day.
    function takePendingDay() {
        if (CalendarEvents.pendingDay === "")
            return;
        openDay(CalendarEvents.pendingDay);
        CalendarEvents.pendingDay = "";
    }

    Component.onCompleted: takePendingDay()
    Connections {
        target: CalendarEvents
        function onPendingDayChanged() {
            root.takePendingDay();
        }
    }

    Keys.onPressed: (event) => {
        if (event.key === Qt.Key_Escape && panelDay !== "") {
            panelDay = "";
            event.accepted = true;
        } else if (event.key === Qt.Key_N && panelDay === "") {
            openDay(newEventDay());
            event.accepted = true;
        } else if ((event.key === Qt.Key_PageDown || event.key === Qt.Key_PageUp)
            && event.modifiers === Qt.NoModifier) {
            if (event.key === Qt.Key_PageDown) {
                monthShift++;
            } else if (event.key === Qt.Key_PageUp) {
                monthShift--;
            }
            event.accepted = true;
        }
    }
    MouseArea {
        anchors.fill: parent
        onWheel: (event) => {
            if (event.angleDelta.y > 0) {
                monthShift--;
            } else if (event.angleDelta.y < 0) {
                monthShift++;
            }
        }
    }

    ColumnLayout {
        id: calendarColumn
        anchors.centerIn: parent
        spacing: 5

        // Calendar header
        RowLayout {
            Layout.fillWidth: true
            spacing: 5
            CalendarHeaderButton {
                clip: true
                buttonText: `${monthShift != 0 ? "• " : ""}${viewingDate.toLocaleDateString(Qt.locale(), "MMMM yyyy")}`
                tooltipText: (monthShift === 0) ? "" : Translation.tr("Jump to current month")
                downAction: () => {
                    monthShift = 0;
                }
            }
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: false
            }
            CalendarHeaderButton {
                forceCircle: true
                tooltipText: Translation.tr("New event")
                downAction: () => {
                    root.openDay(root.newEventDay());
                }
                contentItem: MaterialSymbol {
                    text: "add"
                    iconSize: Appearance.font.pixelSize.larger
                    horizontalAlignment: Text.AlignHCenter
                    color: Appearance.colors.colOnLayer1
                }
            }
            CalendarHeaderButton {
                forceCircle: true
                downAction: () => {
                    monthShift--;
                }
                contentItem: MaterialSymbol {
                    text: "chevron_left"
                    iconSize: Appearance.font.pixelSize.larger
                    horizontalAlignment: Text.AlignHCenter
                    color: Appearance.colors.colOnLayer1
                }
            }
            CalendarHeaderButton {
                forceCircle: true
                downAction: () => {
                    monthShift++;
                }
                contentItem: MaterialSymbol {
                    text: "chevron_right"
                    iconSize: Appearance.font.pixelSize.larger
                    horizontalAlignment: Text.AlignHCenter
                    color: Appearance.colors.colOnLayer1
                }
            }
        }

        // Week days row
        RowLayout {
            id: weekDaysRow
            Layout.alignment: Qt.AlignHCenter
            Layout.fillHeight: false
            spacing: 5
            Repeater {
                model: CalendarLayout.weekDays
                delegate: CalendarDayButton {
                    day: Translation.tr(modelData.day)
                    isToday: modelData.today
                    bold: true
                    enabled: false
                }
            }
        }

        // Real week rows
        Repeater {
            id: calendarRows
            // model: calendarLayout
            model: 6
            delegate: RowLayout {
                Layout.alignment: Qt.AlignHCenter
                Layout.fillHeight: false
                spacing: 5
                Repeater {
                    model: Array(7).fill(modelData)
                    delegate: CalendarDayButton {
                        readonly property string key: root.dayKey(modelData, index)
                        day: calendarLayout[modelData][index].day
                        isToday: calendarLayout[modelData][index].today
                        events: CalendarEvents.counts[key] ?? 0
                        onClicked: root.openDay(key)
                    }
                }
            }
        }
    }

    CalendarDayPanel {
        anchors.fill: parent
        day: root.panelDay
        onDayRequested: key => root.openDay(key)
        onCloseRequested: root.panelDay = ""
    }
}
