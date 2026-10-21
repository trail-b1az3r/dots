import qs.services
import qs.modules.common
import qs.modules.common.widgets
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

/**
 * One day in the calendar: its events, and a new one. Opened by the calendar's + button or a click on a day.
 *
 * A new event has a title, a time (empty for all day; 9, 9:30, 930 and 9:30pm all work), a reminder and, at a
 * time, an alarm that rings until it is stopped (the bell on a listed event turns its alarm on and off). The arrows
 * go to the day before and after.
 */
Item {
    id: root

    property string day: ""
    signal dayRequested(string key)
    signal closeRequested

    component Field: TextField {
        id: field
        padding: 8
        color: activeFocus ? Appearance.m3colors.m3onSurface : Appearance.m3colors.m3onSurfaceVariant
        renderType: Text.NativeRendering
        selectedTextColor: Appearance.m3colors.m3onSecondaryContainer
        selectionColor: Appearance.colors.colSecondaryContainer
        placeholderTextColor: Appearance.m3colors.m3outline
        property bool bad: false
        background: Rectangle {
            radius: Appearance.rounding.verysmall
            border.width: 2
            border.color: field.bad ? Appearance.m3colors.m3error : field.activeFocus ? Appearance.colors.colPrimary : Appearance.m3colors.m3outline
            color: "transparent"
        }
        cursorDelegate: Rectangle {
            width: 1
            color: field.activeFocus ? Appearance.colors.colPrimary : "transparent"
            radius: 1
        }
    }

    // Minutes before, -1 for no reminder; the reminder button goes round these.
    readonly property var reminders: [-1, 5, 15, 60, 1440]
    property int reminderIndex: 2
    readonly property int remind: root.reminders[root.reminderIndex]
    readonly property var dayEvents: root.day === "" ? [] : CalendarEvents.eventsOn(root.day)
    readonly property string parsedTime: CalendarEvents.parseTime(timeInput.text) ?? "invalid"
    readonly property bool canAdd: titleInput.text.trim().length > 0 && root.parsedTime !== "invalid"
    // The alarm for the new event; it needs a time, so it is off while the time is empty.
    property bool alarm: Config.options.calendar.alarm.alarmByDefault
    readonly property bool alarmPossible: root.parsedTime !== "" && root.parsedTime !== "invalid"

    visible: opacity > 0
    opacity: root.day !== "" ? 1 : 0
    z: 9999
    Behavior on opacity {
        NumberAnimation {
            duration: Appearance.animation.elementMoveFast.duration
            easing.type: Appearance.animation.elementMoveFast.type
            easing.bezierCurve: Appearance.animation.elementMoveFast.bezierCurve
        }
    }

    onVisibleChanged: {
        if (!visible) {
            titleInput.text = "";
            timeInput.text = "";
            root.alarm = Config.options.calendar.alarm.alarmByDefault;
        }
    }

    function reminderText(minutes) {
        if (minutes < 0)
            return Translation.tr("No reminder");
        if (minutes < 60)
            return Translation.tr("%1 min before").arg(minutes);
        if (minutes < 1440)
            return Translation.tr("%1 h before").arg(minutes / 60);
        return Translation.tr("A day before");
    }

    function add() {
        if (!root.canAdd)
            return;
        if (CalendarEvents.add(titleInput.text, root.day, timeInput.text, root.remind, root.alarm && root.alarmPossible)) {
            titleInput.text = "";
            timeInput.text = "";
        }
    }

    Rectangle { // Scrim
        anchors.fill: parent
        radius: Appearance.rounding.small
        color: Appearance.colors.colScrim
        MouseArea {
            anchors.fill: parent
            hoverEnabled: true
            preventStealing: true
            onClicked: root.closeRequested()
            onWheel: wheel => wheel.accepted = true
        }
    }

    Rectangle {
        id: dialog
        anchors.fill: parent
        anchors.margins: 8
        color: Appearance.m3colors.m3surfaceContainerHigh
        radius: Appearance.rounding.normal

        MouseArea { // Clicks inside the dialog don't close it
            anchors.fill: parent
            onWheel: wheel => wheel.accepted = true
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 8

            RowLayout {
                Layout.fillWidth: true
                spacing: 4

                CalendarHeaderButton {
                    forceCircle: true
                    tooltipText: Translation.tr("Day before")
                    downAction: () => root.dayRequested(CalendarEvents.addDays(root.day, -1))
                    contentItem: MaterialSymbol {
                        text: "chevron_left"
                        iconSize: Appearance.font.pixelSize.larger
                        horizontalAlignment: Text.AlignHCenter
                        color: Appearance.colors.colOnLayer1
                    }
                }
                StyledText {
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignHCenter
                    elide: Text.ElideRight
                    font.pixelSize: Appearance.font.pixelSize.large
                    color: Appearance.m3colors.m3onSurface
                    text: {
                        const date = CalendarEvents.parseKey(root.day);
                        return date ? date.toLocaleDateString(Qt.locale(), "ddd d MMM") : "";
                    }
                }
                CalendarHeaderButton {
                    forceCircle: true
                    tooltipText: Translation.tr("Day after")
                    downAction: () => root.dayRequested(CalendarEvents.addDays(root.day, 1))
                    contentItem: MaterialSymbol {
                        text: "chevron_right"
                        iconSize: Appearance.font.pixelSize.larger
                        horizontalAlignment: Text.AlignHCenter
                        color: Appearance.colors.colOnLayer1
                    }
                }
                CalendarHeaderButton {
                    forceCircle: true
                    tooltipText: Translation.tr("Close")
                    downAction: () => root.closeRequested()
                    contentItem: MaterialSymbol {
                        text: "close"
                        iconSize: Appearance.font.pixelSize.larger
                        horizontalAlignment: Text.AlignHCenter
                        color: Appearance.colors.colOnLayer1
                    }
                }
            }

            // The day's events
            ListView {
                id: eventList
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 28
                clip: true
                spacing: 2
                model: root.dayEvents

                delegate: RowLayout {
                    id: eventRow
                    required property var modelData
                    width: eventList.width
                    spacing: 8

                    StyledText {
                        Layout.preferredWidth: 52
                        font.pixelSize: Appearance.font.pixelSize.small
                        color: Appearance.colors.colPrimary
                        text: CalendarEvents.describeTime(eventRow.modelData)
                    }
                    StyledText {
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                        color: Appearance.m3colors.m3onSurface
                        text: eventRow.modelData.title
                    }
                    MaterialSymbol {
                        visible: eventRow.modelData.remind >= 0
                        text: "notifications"
                        iconSize: Appearance.font.pixelSize.normal
                        color: Appearance.colors.colSubtext
                    }
                    // The alarm: lit when on. Only an event at a time can have one.
                    RippleButton {
                        visible: (eventRow.modelData.time ?? "") !== ""
                        implicitWidth: 26
                        implicitHeight: 26
                        buttonRadius: Appearance.rounding.full
                        onClicked: CalendarEvents.setAlarm(eventRow.modelData.id, !eventRow.modelData.alarm)
                        contentItem: MaterialSymbol {
                            text: eventRow.modelData.alarm ? "alarm_on" : "alarm_off"
                            horizontalAlignment: Text.AlignHCenter
                            iconSize: Appearance.font.pixelSize.normal
                            fill: eventRow.modelData.alarm ? 1 : 0
                            color: eventRow.modelData.alarm ? Appearance.colors.colPrimary : Appearance.colors.colSubtext
                        }
                        StyledToolTip {
                            text: eventRow.modelData.alarm ? Translation.tr("Alarm on: click to turn it off") : Translation.tr("Ring an alarm at this time")
                        }
                    }
                    RippleButton {
                        implicitWidth: 26
                        implicitHeight: 26
                        buttonRadius: Appearance.rounding.full
                        onClicked: CalendarEvents.remove(eventRow.modelData.id)
                        contentItem: MaterialSymbol {
                            text: "delete"
                            horizontalAlignment: Text.AlignHCenter
                            iconSize: Appearance.font.pixelSize.normal
                            color: Appearance.colors.colOnLayer1
                        }
                        StyledToolTip {
                            text: Translation.tr("Delete")
                        }
                    }
                }

                StyledText {
                    anchors.centerIn: parent
                    visible: eventList.count === 0
                    color: Appearance.colors.colSubtext
                    text: Translation.tr("Nothing on this day")
                }
            }

            Field {
                id: titleInput
                Layout.fillWidth: true
                placeholderText: Translation.tr("New event")
                focus: root.visible
                onAccepted: root.add()
                Keys.onEscapePressed: root.closeRequested()
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 6

                Field {
                    id: timeInput
                    Layout.preferredWidth: 96
                    placeholderText: Translation.tr("All day")
                    bad: root.parsedTime === "invalid"
                    onAccepted: root.add()
                    Keys.onEscapePressed: root.closeRequested()
                    StyledToolTip {
                        text: Translation.tr("A time like 9:30 or 2pm, or empty for all day")
                    }
                }
                DialogButton {
                    Layout.fillWidth: true
                    buttonText: root.reminderText(root.remind)
                    onClicked: root.reminderIndex = (root.reminderIndex + 1) % root.reminders.length
                }
                RippleButton {
                    implicitWidth: 34
                    implicitHeight: 34
                    buttonRadius: Appearance.rounding.full
                    enabled: root.alarmPossible
                    toggled: root.alarm && root.alarmPossible
                    onClicked: root.alarm = !root.alarm
                    contentItem: MaterialSymbol {
                        text: root.alarm && root.alarmPossible ? "alarm_on" : "alarm_add"
                        horizontalAlignment: Text.AlignHCenter
                        iconSize: Appearance.font.pixelSize.larger
                        fill: root.alarm && root.alarmPossible ? 1 : 0
                        color: root.alarm && root.alarmPossible ? Appearance.colors.colOnPrimary : Appearance.colors.colOnLayer1
                        opacity: root.alarmPossible ? 1 : 0.4
                    }
                    StyledToolTip {
                        text: root.alarmPossible ? (root.alarm ? Translation.tr("Alarm on: it rings at this time until you stop it") : Translation.tr("Add an alarm"))
                                                 : Translation.tr("An alarm needs a time")
                    }
                }
                DialogButton {
                    buttonText: Translation.tr("Add")
                    enabled: root.canAdd
                    onClicked: root.add()
                }
            }
        }
    }
}
