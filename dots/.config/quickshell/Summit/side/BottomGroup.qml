pragma ComponentBehavior: Bound

import QtQuick
import qs.common

// The side menu's bottom group, as the Halcyon shell's: the calendar, the to-do list and a timer, as tabs; the arrow
// folds it away to give the notifications the room.
Rectangle {
    id: root
    property int tab: 0
    property bool collapsed: false
    readonly property var tabs: [
        { name: "Calendar", icon: "calendar_month" },
        { name: "To do", icon: "checklist" },
        { name: "Timer", icon: "timer" }
    ]

    implicitHeight: collapsed ? 50 : 312
    Behavior on implicitHeight { NumberAnimation { duration: Theme.enterMs; easing.type: Easing.OutCubic } }
    radius: Theme.radius + 2
    color: Theme.alpha(Theme.text, 0.06)
    clip: true

    Row {
        id: tabRow
        x: 8
        y: 8
        spacing: 4
        Repeater {
            model: root.tabs
            delegate: BarButton {
                required property var modelData
                required property int index
                icon: modelData.icon
                label: root.tab === index || root.collapsed ? modelData.name : ""
                active: root.tab === index && !root.collapsed
                onClicked: {
                    root.tab = index;
                    root.collapsed = false;
                }
            }
        }
    }
    BarButton {
        anchors.right: parent.right
        anchors.rightMargin: 8
        y: 8
        icon: root.collapsed ? "expand_less" : "expand_more"
        onClicked: root.collapsed = !root.collapsed
    }

    Item {
        id: page
        anchors.top: tabRow.bottom
        anchors.topMargin: 10
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 12
        x: 14
        width: parent.width - 28
        opacity: root.collapsed ? 0 : 1
        Behavior on opacity { NumberAnimation { duration: Theme.animMs } }

        MonthView {
            width: parent.width
            visible: root.tab === 0
        }
        TodoList {
            anchors.fill: parent
            visible: root.tab === 1
        }
        TimerView {
            anchors.fill: parent
            visible: root.tab === 2
        }
    }
}
