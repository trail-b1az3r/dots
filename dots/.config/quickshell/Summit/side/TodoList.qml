pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import qs.common

// To do: the Halcyon shell's list (~/.local/state/quickshell/user/todo.json, [{content, done}]), so it is the same
// list under either shell. Type and Enter to add; click the circle to tick it off; the bin removes it.
Item {
    id: root
    property var items: []
    readonly property string path: (Quickshell.env("XDG_STATE_HOME") || (Quickshell.env("HOME") + "/.local/state")) + "/quickshell/user/todo.json"

    function save(next) {
        root.items = next;
        file.setText(JSON.stringify(next));
    }

    FileView {
        id: file
        path: root.path
        watchChanges: true
        printErrors: false
        onFileChanged: reload()
        onLoaded: {
            try {
                const list = JSON.parse(text());
                root.items = Array.isArray(list) ? list : [];
            } catch (e) {
                root.items = [];
            }
        }
        onLoadFailed: root.items = []
    }

    TextField {
        id: input
        width: parent.width
        height: 38
        placeholderText: "Add a task"
        placeholderTextColor: Theme.muted
        color: Theme.text
        font.family: Theme.font
        font.pixelSize: 13
        leftPadding: 14
        background: Rectangle {
            radius: 19
            color: Theme.alpha(Theme.text, input.activeFocus ? 0.12 : 0.08)
        }
        onAccepted: {
            const content = text.trim();
            if (content === "")
                return;
            root.save([...root.items, { content, done: false }]);
            text = "";
        }
    }

    ListView {
        id: list
        anchors.top: input.bottom
        anchors.topMargin: 8
        anchors.bottom: parent.bottom
        width: parent.width
        clip: true
        spacing: 2
        // Not done first.
        model: root.items.map((item, index) => ({ item, index })).sort((a, b) => a.item.done - b.item.done)
        delegate: Rectangle {
            id: row
            required property var modelData
            width: list.width
            height: Math.max(36, text.implicitHeight + 14)
            radius: 12
            color: rowArea.containsMouse ? Theme.alpha(Theme.text, 0.07) : "transparent"
            MouseArea {
                id: rowArea
                anchors.fill: parent
                hoverEnabled: true
            }
            BarButton {
                id: tick
                x: 2
                anchors.verticalCenter: parent.verticalCenter
                implicitHeight: 30
                icon: row.modelData.item.done ? "check_circle" : "radio_button_unchecked"
                tint: row.modelData.item.done ? Theme.accent : Theme.text
                onClicked: {
                    const next = root.items.slice();
                    next[row.modelData.index] = { content: row.modelData.item.content, done: !row.modelData.item.done };
                    root.save(next);
                }
            }
            Text {
                id: text
                anchors.left: tick.right
                anchors.leftMargin: 4
                anchors.right: bin.left
                anchors.verticalCenter: parent.verticalCenter
                text: row.modelData.item.content
                wrapMode: Text.Wrap
                color: row.modelData.item.done ? Theme.muted : Theme.text
                font.family: Theme.font
                font.pixelSize: 13
                font.strikeout: row.modelData.item.done
            }
            BarButton {
                id: bin
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                implicitHeight: 28
                icon: "delete"
                opacity: rowArea.containsMouse || hovered ? 0.9 : 0
                property bool hovered: false
                onClicked: root.save(root.items.filter((_, i) => i !== row.modelData.index))
            }
        }
    }

    Text {
        anchors.centerIn: list
        visible: root.items.length === 0
        text: "Nothing to do"
        color: Theme.muted
        font.family: Theme.font
        font.pixelSize: 13
    }
}
