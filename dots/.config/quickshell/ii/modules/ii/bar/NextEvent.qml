import qs.services
import qs.modules.common
import qs.modules.common.widgets
import QtQuick
import QtQuick.Layouts

/**
 * The next calendar event in the coming week, from the right sidebar's calendar: "14:30 Dentist", "Tomorrow ·
 * Dentist". A click opens the calendar on its day. Hidden when there is nothing coming up. Settings > Bar >
 * Next calendar event turns it off.
 */
RippleButton {
    id: root

    readonly property var event: CalendarEvents.next
    readonly property int days: root.event ? CalendarEvents.daysAway(root.event) : -1
    readonly property bool shown: root.event !== null && root.days >= 0 && root.days <= 6
    readonly property bool soon: root.days === 0 && root.event?.time !== "" && root.minutesAway <= 15
    readonly property real minutesAway: {
        if (!root.event?.time)
            return Infinity;
        const parts = root.event.time.split(":");
        const start = CalendarEvents.parseKey(root.event.date);
        start.setHours(Number(parts[0]), Number(parts[1]));
        return (start.getTime() - CalendarEvents.now.getTime()) / 60000;
    }

    function whenText() {
        if (!root.event)
            return "";
        if (root.days === 0)
            return root.event.time !== "" ? root.event.time : Translation.tr("Today");
        const day = root.days === 1 ? Translation.tr("Tomorrow") : CalendarEvents.parseKey(root.event.date).toLocaleDateString(Qt.locale(), "ddd");
        return root.event.time !== "" ? `${day} ${root.event.time}` : day;
    }

    visible: root.shown
    implicitHeight: 28
    implicitWidth: row.implicitWidth + 12 * 2
    buttonRadius: Appearance.rounding.full
    colBackground: root.soon ? Appearance.colors.colSecondaryContainer : Appearance.colors.colLayer1
    colBackgroundHover: root.soon ? Appearance.colors.colSecondaryContainerHover : Appearance.colors.colLayer1Hover
    colRipple: Appearance.colors.colLayer1Active
    onClicked: CalendarEvents.open(root.event.date)

    RowLayout {
        id: row
        anchors.centerIn: parent
        spacing: 6

        MaterialSymbol {
            text: root.soon ? "notifications_active" : "event_upcoming"
            iconSize: Appearance.font.pixelSize.large
            color: Appearance.colors.colOnLayer1
        }
        StyledText {
            text: root.whenText()
            font.pixelSize: Appearance.font.pixelSize.small
            color: Appearance.colors.colPrimary
        }
        StyledText {
            Layout.maximumWidth: 160
            elide: Text.ElideRight
            text: root.event?.title ?? ""
            font.pixelSize: Appearance.font.pixelSize.small
            color: Appearance.colors.colOnLayer1
        }
    }

    StyledToolTip {
        text: Translation.tr("Next event: open the calendar")
    }
}
