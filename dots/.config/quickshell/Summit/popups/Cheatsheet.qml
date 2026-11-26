pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Hyprland
import qs.common
import qs.services
import "../services/keys.js" as KeyList

// The keys cheat sheet (Super+/; Super+Shift+/ the hypr keys): a large pane of frosted glass over the focused screen
// with every Hyprland bind that has a description, in cards by what they are for ("Window", "Workspace", "Shell"...),
// each a row of keycaps (Super, Ctrl, Shift, Alt, Fn and Hyper with Summit's own icons) and what it does. Type to
// find one; Enter runs the first found, a click runs any; Alt+H switches between the keys and the hypr keys (the
// Hyper chords and hypr mode's keys). Esc, a click outside or the same key again closes it. When Summit is not
// running the keys open the same list in Rofi (halcyon/summit/rofi-menu keys).
Scope {
    id: root

    property bool shown: false
    property string page: "all"
    property var binds: []
    property string query: ""

    readonly property var rows: KeyList.rows(root.binds, root.page).filter(r => KeyList.matches(r, root.query))
    readonly property var groups: KeyList.groups(root.rows)

    function open(which) {
        root.page = which;
        root.query = "";
        bindsProc.running = true;
        root.shown = true;
    }
    function toggle(which) {
        if (root.shown && root.page === which)
            root.shown = false;
        else
            root.open(which);
    }
    // Run a bind as Hyprland would; a key of hypr mode turns the mode on (it only works there).
    function run(row) {
        if (!row?.runnable)
            return;
        root.shown = false;
        if (row.inMode)
            Quickshell.execDetached(["sh", "-c", "[ \"$(hyprctl dispatch 'hl.dsp.submap(\"hypr\")')\" = ok ] || hyprctl dispatch submap hypr"]);
        else if (row.dispatcher === "exec" && row.arg !== "")
            Quickshell.execDetached(["sh", "-c", "[ \"$(hyprctl dispatch \"$1\")\" = ok ] || hyprctl dispatch exec \"$2\"", "sh",
                "hl.dsp.exec_cmd(" + JSON.stringify(row.arg) + ")", row.arg]);
        else
            Quickshell.execDetached(row.arg !== "" ? ["hyprctl", "dispatch", row.dispatcher, row.arg] : ["hyprctl", "dispatch", row.dispatcher]);
    }

    Process {
        id: bindsProc
        command: ["hyprctl", "binds", "-j"]
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    root.binds = JSON.parse(text);
                } catch (e) {
                    root.binds = [];
                }
            }
        }
    }

    LazyLoader {
        active: root.shown

        PanelWindow {
            id: window
            screen: Quickshell.screens.find(s => s.name === Hyprland.focusedMonitor?.name) ?? Quickshell.screens[0]
            color: "transparent"
            WlrLayershell.namespace: "summit-cheatsheet"
            WlrLayershell.layer: WlrLayer.Overlay
            WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive
            exclusionMode: ExclusionMode.Ignore
            anchors { top: true; bottom: true; left: true; right: true }

            // The screen dims a little behind it; a click there closes it.
            Rectangle {
                anchors.fill: parent
                color: Theme.alpha("#000000", 0.28 * card.opacity)
                MouseArea {
                    anchors.fill: parent
                    onClicked: root.shown = false
                }
            }

            Glass {
                id: card
                anchors.centerIn: parent
                width: Math.min(parent.width - 96, 1640)
                height: Math.min(parent.height - 120, 980)
                radius: Theme.radius + 10
                tint: Theme.glassTint + 0.3
                opacity: 0
                scale: 0.95
                Component.onCompleted: enter.start()
                ParallelAnimation {
                    id: enter
                    NumberAnimation { target: card; property: "opacity"; to: 1; duration: Theme.animMs + 60; easing.type: Easing.OutCubic }
                    NumberAnimation { target: card; property: "scale"; to: 1; duration: Theme.enterMs; easing.type: Easing.OutBack; easing.overshoot: 1.2 }
                }
                // Clicks on the pane stay on it.
                MouseArea { anchors.fill: parent }

                // The top: its name, the two pages, and the search.
                Item {
                    id: head
                    x: 28
                    y: 22
                    width: parent.width - 56
                    height: 46

                    Row {
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 14
                        KeyIcon {
                            kind: root.page === "hypr" ? "hyper" : "super"
                            size: 28
                            stroke: 2.2
                            color: Theme.accent
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            text: root.page === "hypr" ? "Hypr keys" : "Keys"
                            color: Theme.text
                            font.family: Theme.font
                            font.pixelSize: 26
                            font.weight: Font.DemiBold
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Row {
                            spacing: 4
                            leftPadding: 10
                            anchors.verticalCenter: parent.verticalCenter
                            Repeater {
                                model: [{ id: "all", name: "Keys" }, { id: "hypr", name: "Hypr keys" }]
                                delegate: BarButton {
                                    required property var modelData
                                    label: modelData.name
                                    active: root.page === modelData.id
                                    onClicked: root.page = modelData.id
                                }
                            }
                        }
                    }

                    TextField {
                        id: search
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        width: Math.min(380, parent.width * 0.32)
                        height: 42
                        focus: true
                        placeholderText: "Find a key"
                        placeholderTextColor: Theme.muted
                        color: Theme.text
                        font.family: Theme.font
                        font.pixelSize: 15
                        leftPadding: 42
                        background: Rectangle {
                            radius: 21
                            color: Theme.alpha(Theme.text, search.activeFocus ? 0.12 : 0.08)
                            Symbol {
                                x: 14
                                anchors.verticalCenter: parent.verticalCenter
                                name: "search"
                                color: Theme.muted
                            }
                        }
                        onTextChanged: root.query = text
                        Component.onCompleted: forceActiveFocus()
                        Keys.onEscapePressed: root.shown = false
                        Keys.onReturnPressed: root.run(root.rows.find(r => r.runnable))
                        Keys.onPressed: event => {
                            if (event.key === Qt.Key_H && (event.modifiers & Qt.AltModifier)) {
                                root.page = root.page === "hypr" ? "all" : "hypr";
                                event.accepted = true;
                            }
                        }
                    }
                }

                Text {
                    id: hint
                    x: 28
                    anchors.top: head.bottom
                    anchors.topMargin: 6
                    width: parent.width - 56
                    text: root.page === "hypr"
                        ? "Hyper is Super + Ctrl + Alt + Shift (or one key mapped to all four). Mode keys work while hypr mode is on (Super + Ctrl + H; Esc leaves). Click one to run it · Alt+H the keys · Esc closes"
                        : "Fn keys are the top row's media and brightness keys (with Fn on most laptops). Click one to run it · Enter runs the first found · Alt+H the hypr keys · Esc closes"
                    color: Theme.muted
                    font.family: Theme.font
                    font.pixelSize: 13
                    elide: Text.ElideRight
                }

                // The cards, in columns as wide as the pane allows, each column as long as the others.
                Flickable {
                    id: body
                    anchors.top: hint.bottom
                    anchors.topMargin: 18
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 22
                    x: 22
                    width: parent.width - 44
                    clip: true
                    contentHeight: columnsRow.implicitHeight
                    boundsBehavior: Flickable.StopAtBounds
                    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                    readonly property int columnCount: Math.max(1, Math.floor((width + 16) / 400))
                    readonly property real columnWidth: (width - 16 * (columnCount - 1)) / columnCount

                    Row {
                        id: columnsRow
                        spacing: 16
                        Repeater {
                            model: KeyList.columns(root.groups, body.columnCount)
                            delegate: Column {
                                id: column
                                required property var modelData
                                width: body.columnWidth
                                spacing: 16
                                Repeater {
                                    model: column.modelData
                                    delegate: Rectangle {
                                        id: group
                                        required property var modelData
                                        width: column.width
                                        implicitHeight: groupCol.implicitHeight + 24
                                        radius: Theme.radius + 2
                                        color: Theme.alpha(Theme.text, 0.05)
                                        Column {
                                            id: groupCol
                                            x: 14
                                            y: 12
                                            width: parent.width - 28
                                            spacing: 4
                                            Text {
                                                text: group.modelData.name
                                                color: Theme.accent
                                                font.family: Theme.font
                                                font.pixelSize: 13
                                                font.weight: Font.Bold
                                                font.capitalization: Font.AllUppercase
                                                font.letterSpacing: 1
                                                bottomPadding: 6
                                            }
                                            Repeater {
                                                model: group.modelData.rows
                                                delegate: Rectangle {
                                                    id: line
                                                    required property var modelData
                                                    width: groupCol.width
                                                    height: Math.max(40, keysFlow.implicitHeight + 10)
                                                    radius: 10
                                                    color: lineArea.containsMouse && line.modelData.runnable ? Theme.alpha(Theme.accent, 0.14) : "transparent"
                                                    Behavior on color { ColorAnimation { duration: Theme.animMs } }
                                                    Flow {
                                                        id: keysFlow
                                                        x: 4
                                                        anchors.verticalCenter: parent.verticalCenter
                                                        // The keys in a column of their own, so what they do lines up.
                                                        width: parent.width * 0.5
                                                        spacing: 5
                                                        Repeater {
                                                            model: line.modelData.caps
                                                            delegate: KeyCap {
                                                                required property var modelData
                                                                kind: modelData.kind
                                                                label: modelData.label
                                                                size: 30
                                                            }
                                                        }
                                                    }
                                                    Text {
                                                        anchors.left: keysFlow.right
                                                        anchors.leftMargin: 12
                                                        anchors.right: parent.right
                                                        anchors.rightMargin: 6
                                                        anchors.verticalCenter: parent.verticalCenter
                                                        text: line.modelData.text
                                                        color: Theme.text
                                                        font.family: Theme.font
                                                        font.pixelSize: 14
                                                        wrapMode: Text.Wrap
                                                        maximumLineCount: 2
                                                        elide: Text.ElideRight
                                                    }
                                                    MouseArea {
                                                        id: lineArea
                                                        anchors.fill: parent
                                                        hoverEnabled: true
                                                        cursorShape: line.modelData.runnable ? Qt.PointingHandCursor : Qt.ArrowCursor
                                                        onClicked: root.run(line.modelData)
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                Text {
                    anchors.centerIn: body
                    visible: root.rows.length === 0
                    text: root.binds.length === 0 ? "Hyprland gave no keys" : "No key matches “" + root.query + "”"
                    color: Theme.muted
                    font.family: Theme.font
                    font.pixelSize: 16
                }
            }
        }
    }
}
