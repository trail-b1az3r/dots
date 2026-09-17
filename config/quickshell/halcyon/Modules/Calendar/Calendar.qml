import QtQuick
import QtQuick.Layouts
import Quickshell
import qs.Config
import qs.Components
import qs.Services

/**
 * The clock and calendar.
 *
 * A month grid and the time, in the shape people expect from clicking
 * the clock. The `SystemClock` only ticks while this is open, which is
 * the difference between a calendar and a timer that runs all day.
 */
OverlayWindow {
    id: root

    name: "calendar"
    namespaceName: "halcyon-overlay"
    origin: "top"
    scrim: false
    grabKeyboard: false

    property int monthOffset: 0
    onOpened: root.monthOffset = 0

    SystemClock {
        id: clock
        enabled: root.shown
        precision: SystemClock.Minutes
    }

    readonly property date shownMonth: {
        const now = clock.date ?? new Date();
        return new Date(now.getFullYear(), now.getMonth() + root.monthOffset, 1);
    }

    readonly property var grid: {
        const first = root.shownMonth;
        const year = first.getFullYear();
        const month = first.getMonth();
        // Monday-first, which is what most of the world uses and what the
        // weekday header below assumes.
        const leading = (first.getDay() + 6) % 7;
        const days = new Date(year, month + 1, 0).getDate();
        const today = clock.date ?? new Date();

        const cells = [];
        for (let i = 0; i < leading; i++)
            cells.push({ day: 0, today: false });
        for (let day = 1; day <= days; day++) {
            cells.push({
                day: day,
                today: day === today.getDate()
                    && month === today.getMonth()
                    && year === today.getFullYear()
            });
        }
        while (cells.length % 7 !== 0)
            cells.push({ day: 0, today: false });
        return cells;
    }

    GlassSurface {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: Config.get("bar.height", 34) + Theme.spacingSm

        width: 320
        height: column.implicitHeight + padding * 2
        level: 4
        radius: Theme.radiusXl
        padding: Theme.panelPadding

        ColumnLayout {
            id: column
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingSm

            Label {
                Layout.alignment: Qt.AlignHCenter
                text: Qt.formatDateTime(clock.date ?? new Date(), "HH:mm")
                variant: "display"
            }

            Label {
                Layout.alignment: Qt.AlignHCenter
                text: Qt.formatDateTime(clock.date ?? new Date(), "dddd, d MMMM yyyy")
                variant: "footnote"
                tone: "secondary"
            }

            Separator { Layout.fillWidth: true }

            RowLayout {
                Layout.fillWidth: true

                GlassIconButton {
                    glyph: "󰅁"
                    size: 26
                    iconSize: 12
                    tooltip: "Previous month"
                    onClicked: root.monthOffset -= 1
                }

                Label {
                    Layout.fillWidth: true
                    text: Qt.formatDateTime(root.shownMonth, "MMMM yyyy")
                    variant: "body"
                    font.weight: Theme.weightMedium
                    horizontalAlignment: Text.AlignHCenter
                }

                GlassIconButton {
                    glyph: "󰅂"
                    size: 26
                    iconSize: 12
                    tooltip: "Next month"
                    onClicked: root.monthOffset += 1
                }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: 7
                columnSpacing: 0
                rowSpacing: 2

                Repeater {
                    model: ["M", "T", "W", "T", "F", "S", "S"]

                    Label {
                        required property var modelData
                        Layout.fillWidth: true
                        text: modelData
                        variant: "caption"
                        tone: "tertiary"
                        horizontalAlignment: Text.AlignHCenter
                    }
                }

                Repeater {
                    model: root.grid

                    Item {
                        required property var modelData
                        Layout.fillWidth: true
                        Layout.preferredHeight: 30

                        Rectangle {
                            anchors.centerIn: parent
                            width: 26
                            height: 26
                            radius: width / 2
                            visible: modelData.today
                            color: Theme.accent
                        }

                        Label {
                            anchors.centerIn: parent
                            visible: modelData.day > 0
                            text: String(modelData.day)
                            variant: "footnote"
                            color: modelData.today ? Theme.onAccent : Theme.text
                            font.weight: modelData.today
                                ? Theme.weightSemibold
                                : Theme.weightRegular
                        }
                    }
                }
            }
        }
    }
}
