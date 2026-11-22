pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import qs.common

// This month, with today marked; scroll or the arrows to move between months. Opens under the clock.
PopupWindow {
    id: root
    property date date: new Date()
    property int offset: 0
    readonly property date shown: new Date(date.getFullYear(), date.getMonth() + offset, 1)
    visible: false
    color: "transparent"
    implicitWidth: 300
    implicitHeight: body.implicitHeight

    onVisibleChanged: if (visible) offset = 0

    Glass {
        id: body
        width: parent.width
        implicitHeight: col.implicitHeight + 28
        radius: Theme.radius + 4
        tint: Theme.glassTint + 0.18

        Column {
            id: col
            x: 14
            y: 14
            width: parent.width - 28
            spacing: 10

            Row {
                width: parent.width
                Text {
                    width: parent.width - 64
                    text: Qt.formatDate(root.shown, "MMMM yyyy")
                    color: Theme.text
                    font.family: Theme.font
                    font.pixelSize: 15
                    font.weight: Font.DemiBold
                }
                BarButton { icon: "chevron_left"; implicitHeight: 26; onClicked: root.offset-- }
                BarButton { icon: "chevron_right"; implicitHeight: 26; onClicked: root.offset++ }
            }

            Grid {
                columns: 7
                spacing: 2
                Repeater {
                    model: ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
                    delegate: Text {
                        required property string modelData
                        width: 36; height: 22
                        text: modelData
                        horizontalAlignment: Text.AlignHCenter
                        color: Theme.muted
                        font.family: Theme.font
                        font.pixelSize: 11
                    }
                }
                Repeater {
                    // Monday-first weeks: blanks before the 1st, then the month's days.
                    model: {
                        const first = (root.shown.getDay() + 6) % 7;
                        const days = new Date(root.shown.getFullYear(), root.shown.getMonth() + 1, 0).getDate();
                        return Array.from({ length: first + days }, (_, i) => i < first ? 0 : i - first + 1);
                    }
                    delegate: Rectangle {
                        required property int modelData
                        readonly property bool today: root.offset === 0 && modelData === root.date.getDate()
                        width: 36; height: 30
                        radius: 10
                        color: today ? Theme.accent : "transparent"
                        Text {
                            anchors.centerIn: parent
                            visible: parent.modelData > 0
                            text: parent.modelData
                            color: parent.today ? Theme.accentText : Theme.text
                            font.family: Theme.font
                            font.pixelSize: 13
                            font.weight: parent.today ? Font.DemiBold : Font.Normal
                        }
                    }
                }
            }
        }

        WheelHandler { onWheel: event => root.offset += event.angleDelta.y > 0 ? -1 : 1 }
    }
}
