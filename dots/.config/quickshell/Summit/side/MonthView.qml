pragma ComponentBehavior: Bound

import QtQuick
import qs.common

// A month, Monday first, today in the accent; the arrows or the wheel move between months.
Column {
    id: root
    property int offset: 0
    readonly property date today: new Date()
    readonly property date shown: new Date(today.getFullYear(), today.getMonth() + offset, 1)
    spacing: 8

    // The 42 days on the grid: from the Monday on or before the 1st.
    readonly property var days: {
        const first = new Date(shown.getFullYear(), shown.getMonth(), 1);
        const lead = (first.getDay() + 6) % 7;
        const out = [];
        for (let i = 0; i < 42; i++)
            out.push(new Date(first.getFullYear(), first.getMonth(), 1 - lead + i));
        return out;
    }

    Item {
        width: parent.width
        height: 28
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: Qt.formatDate(root.shown, "MMMM yyyy")
            color: Theme.text
            font.family: Theme.font
            font.pixelSize: 14
            font.weight: Font.DemiBold
        }
        Row {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            BarButton { icon: "chevron_left"; implicitHeight: 26; onClicked: root.offset-- }
            BarButton { icon: "chevron_right"; implicitHeight: 26; onClicked: root.offset++ }
        }
    }

    Grid {
        id: grid
        columns: 7
        width: parent.width
        readonly property real cell: width / 7
        Repeater {
            model: ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
            delegate: Text {
                required property string modelData
                width: grid.cell
                height: 22
                text: modelData
                horizontalAlignment: Text.AlignHCenter
                color: Theme.muted
                font.family: Theme.font
                font.pixelSize: 11
                font.weight: Font.Medium
            }
        }
        Repeater {
            model: root.days
            delegate: Item {
                id: day
                required property var modelData
                readonly property bool isToday: modelData.toDateString() === root.today.toDateString()
                readonly property bool inMonth: modelData.getMonth() === root.shown.getMonth()
                width: grid.cell
                height: 30
                Rectangle {
                    anchors.centerIn: parent
                    width: 28
                    height: 28
                    radius: 14
                    color: day.isToday ? Theme.accent : "transparent"
                }
                Text {
                    anchors.centerIn: parent
                    text: day.modelData.getDate()
                    color: day.isToday ? Theme.accentText : day.inMonth ? Theme.text : Theme.alpha(Theme.text, 0.3)
                    font.family: Theme.font
                    font.pixelSize: 12
                    font.weight: day.isToday ? Font.Bold : Font.Normal
                }
            }
        }
    }

    WheelHandler {
        onWheel: event => root.offset += event.angleDelta.y > 0 ? -1 : 1
    }
}
