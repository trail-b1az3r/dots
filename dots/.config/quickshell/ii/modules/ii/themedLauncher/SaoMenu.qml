pragma ComponentBehavior: Bound

import qs
import qs.services
import qs.modules.common
import QtQuick
import Quickshell

/**
 * Sword Art Online system menu. Original Quickshell UI built around the 2D game-menu
 * layout: left insignia rail, player/equipment card, radial gear slots and a
 * horizontal metallic selection list. The Apps page launches real desktop entries.
 */
Item {
    id: menu
    property var host
    signal closed

    readonly property color gold: "#E5A900"
    readonly property color goldLight: "#FFC928"
    readonly property color panel: "#D9D9D7"
    readonly property color dark: "#292B2D"
    readonly property color ink: "#343638"
    readonly property color muted: "#777A7B"
    readonly property var categories: [
        { title: "Player", glyph: "P" },
        { title: "Items", glyph: "I" },
        { title: "Skills", glyph: "S" },
        { title: "Quests", glyph: "Q" },
        { title: "Map", glyph: "M" },
        { title: "System", glyph: "X" }
    ]
    property int category: 0
    property int selected: 0
    property string query: ""
    property var allApps: []
    readonly property var apps: query === "" ? allApps : AppSearch.fuzzyQuery(query)
    readonly property var visibleApps: category === 0 ? apps : []

    function open() {
        closing = false;
        allApps = host ? host.apps() : [];
        category = 0;
        selected = 0;
        query = "";
        appear = 0;
        forceActiveFocus();
        entrance.restart();
    }
    function close() {
        if (!closing) {
            closing = true;
            exitAnim.start();
        }
    }
    function chooseCategory(index) {
        category = index;
        selected = 0;
        query = "";
    }
    function launchSelected() {
        if (category === 0 && visibleApps.length > 0)
            host.launchEntry(visibleApps[Math.min(selected, visibleApps.length - 1)]);
    }

    property real appear: 0
    property bool closing: false
    NumberAnimation { id: entrance; target: menu; property: "appear"; to: 1; duration: 260; easing.type: Easing.OutCubic }
    SequentialAnimation {
        id: exitAnim
        NumberAnimation { target: menu; property: "appear"; to: 0; duration: 170; easing.type: Easing.InCubic }
        ScriptAction { script: { menu.closing = false; menu.closed(); } }
    }

    focus: true
    Keys.onPressed: event => {
        if (event.key === Qt.Key_Escape) {
            if (menu.query !== "") menu.query = "";
            else menu.host.dismiss();
        } else if (event.key === Qt.Key_Up) {
            if (menu.category === 0) menu.selected = Math.max(0, menu.selected - 1);
        } else if (event.key === Qt.Key_Down) {
            if (menu.category === 0) menu.selected = Math.min(menu.visibleApps.length - 1, menu.selected + 1);
        } else if (event.key === Qt.Key_Left) {
            menu.chooseCategory((menu.category + menu.categories.length - 1) % menu.categories.length);
        } else if (event.key === Qt.Key_Right || event.key === Qt.Key_Tab) {
            menu.chooseCategory((menu.category + 1) % menu.categories.length);
        } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
            menu.launchSelected();
        } else if (event.key === Qt.Key_Backspace) {
            menu.query = menu.query.slice(0, -1);
            menu.selected = 0;
        } else if (event.text.length === 1 && event.text >= " ") {
            menu.query += event.text;
            menu.category = 0;
            menu.selected = 0;
        } else return;
        event.accepted = true;
    }

    Rectangle {
        anchors.fill: parent
        color: "#A626282A"
        opacity: menu.appear
        MouseArea { anchors.fill: parent; onClicked: menu.host.dismiss() }
    }

    Item {
        id: composition
        anchors.centerIn: parent
        width: Math.min(parent.width * 0.91, 1320)
        height: Math.min(parent.height * 0.82, 760)
        opacity: menu.appear
        scale: 0.97 + menu.appear * 0.03

        MouseArea { anchors.fill: parent }
        Rectangle {
            x: 0; y: 0; width: 54; height: parent.height
            color: menu.gold
            Text {
                anchors.centerIn: parent
                text: "SAO"
                color: "#FFF4CF"
                font.pixelSize: 25
                font.bold: true
                rotation: -90
            }
            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 24
                width: 28; height: 28; radius: 14
                color: "#FFF2C5"
                Text { anchors.centerIn: parent; text: "A"; color: menu.gold; font.bold: true; font.pixelSize: 18 }
            }
        }

        // Player status and equipment diagram.
        Rectangle {
            x: 92; y: 28; width: 390; height: parent.height - 56
            color: menu.panel
            border.color: "#F4F4F2"
            border.width: 2
            Column {
                anchors.fill: parent
                anchors.margins: 18
                spacing: 10
                Text {
                    width: parent.width
                    text: menu.categories[menu.category].title.toUpperCase()
                    color: menu.ink
                    font.pixelSize: 17
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                }
                Rectangle { width: parent.width; height: 1; color: "#8C8D8B" }
                Item {
                    width: parent.width
                    height: parent.height * 0.61
                    Repeater {
                        model: 12
                        delegate: Rectangle {
                            required property int index
                            width: 22; height: 22; radius: 11
                            x: parent.width / 2 - width / 2 + Math.cos(index * Math.PI / 6) * 118 - 11
                            y: parent.height / 2 - height / 2 + Math.sin(index * Math.PI / 6) * 118 - 11
                            color: index === 8 ? menu.gold : "#66696A"
                            border.width: 3; border.color: "#B8B9B7"
                            Rectangle { anchors.centerIn: parent; width: 8; height: 8; radius: 4; color: "#E5E5E3" }
                        }
                    }
                    // Abstract player silhouette, deliberately drawn from primitives.
                    Rectangle { anchors.horizontalCenter: parent.horizontalCenter; y: 32; width: 22; height: 22; radius: 11; color: "#414446" }
                    Rectangle { anchors.horizontalCenter: parent.horizontalCenter; y: 57; width: 30; height: 70; radius: 8; color: "#414446" }
                    Rectangle { x: parent.width / 2 - 29; y: 62; width: 12; height: 68; rotation: 10; radius: 5; color: "#414446" }
                    Rectangle { x: parent.width / 2 + 17; y: 62; width: 12; height: 68; rotation: -10; radius: 5; color: "#414446" }
                    Rectangle { x: parent.width / 2 - 25; y: 120; width: 13; height: 88; rotation: 8; radius: 5; color: "#414446" }
                    Rectangle { x: parent.width / 2 + 12; y: 120; width: 13; height: 88; rotation: -8; radius: 5; color: "#414446" }
                }
                Rectangle { width: parent.width; height: 1; color: "#8C8D8B" }
                Text {
                    text: menu.category === 0 ? "PLAYER STATUS" : menu.categories[menu.category].title.toUpperCase()
                    color: menu.ink; font.pixelSize: 15; font.bold: true
                }
                Text {
                    width: parent.width
                    text: menu.category === 0 ? "LEVEL  |  ONLINE\nHP  ██████████  100%\nSTATUS  |  READY" : "SYSTEM PANEL\nSelect an entry from the menu."
                    color: menu.ink; font.pixelSize: 13; lineHeight: 1.3
                }
            }
        }

        // Round category selector, echoing the game radial menu.
        Column {
            x: 502; anchors.verticalCenter: parent.verticalCenter
            spacing: 12
            Repeater {
                model: menu.categories
                delegate: Rectangle {
                    required property var modelData
                    required property int index
                    width: 56; height: 56; radius: 28
                    color: menu.category === index ? menu.gold : "#777A7B"
                    border.width: menu.category === index ? 3 : 2
                    border.color: menu.category === index ? "#FFE08A" : "#B8B9B9"
                    Text {
                        anchors.centerIn: parent
                        text: modelData.glyph
                        color: menu.category === index ? "#FFFFFF" : "#DADAD8"
                        font.pixelSize: 21; font.bold: true
                    }
                    MouseArea { anchors.fill: parent; onClicked: menu.chooseCategory(index) }
                }
            }
        }

        // Metallic horizontal submenu, with a bright gold selected row.
        Rectangle {
            x: 590; y: 28; width: parent.width - x - 8; height: parent.height - 56
            color: "#343638"
            border.width: 1; border.color: "#66696A"
            Column {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 8
                Row {
                    width: parent.width
                    Text {
                        text: menu.categories[menu.category].title.toUpperCase()
                        color: "#F2F2EF"; font.pixelSize: 17; font.bold: true
                    }
                    Text {
                        anchors.right: parent.right
                        text: "SYSTEM MENU"
                        color: "#AEB1B1"; font.pixelSize: 11
                    }
                }
                Rectangle {
                    width: parent.width; height: 38
                    color: "#BFC1BF"; border.color: "#E7E8E6"
                    TextInput {
                        anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 8
                        verticalAlignment: TextInput.AlignVCenter
                        color: "#303234"; font.pixelSize: 14
                        text: menu.query
                        onTextEdited: { menu.query = text; menu.selected = 0; }
                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            visible: parent.text === ""
                            text: "Search applications..."
                            color: "#777A7B"; font.pixelSize: 13
                        }
                    }
                }
                Item {
                    width: parent.width; height: parent.height - 94
                    clip: true
                    ListView {
                        anchors.fill: parent
                        model: menu.visibleApps
                        spacing: 4
                        currentIndex: menu.selected
                        delegate: Rectangle {
                            required property var modelData
                            required property int index
                            width: ListView.view.width; height: 43
                            color: index === menu.selected ? menu.gold : "#D7D8D6"
                            border.width: 1
                            border.color: index === menu.selected ? "#FFE08A" : "#A5A7A5"
                            Row {
                                anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 12
                                spacing: 12
                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "◉"
                                    color: index === menu.selected ? "#FFFFFF" : "#55595A"
                                    font.pixelSize: 17
                                }
                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: parent.width - 48
                                    text: modelData.name ?? "Application"
                                    color: "#303234"
                                    font.pixelSize: 14
                                    elide: Text.ElideRight
                                }
                            }
                            MouseArea {
                                anchors.fill: parent
                                onEntered: menu.selected = index
                                onClicked: { menu.selected = index; menu.launchSelected(); }
                            }
                        }
                    }
                    Text {
                        anchors.centerIn: parent
                        visible: menu.category !== 0
                        text: menu.categories[menu.category].title + "\n\nThis section is ready for its game-style panel."
                        color: "#E3E4E1"; font.pixelSize: 16
                        horizontalAlignment: Text.AlignHCenter
                    }
                    Text {
                        anchors.centerIn: parent
                        visible: menu.category === 0 && menu.visibleApps.length === 0
                        text: "No matching applications"
                        color: "#D7D8D6"; font.pixelSize: 14
                    }
                }
                Text {
                    width: parent.width
                    text: "↑ ↓ SELECT     ENTER CONFIRM     ESC BACK"
                    color: "#AEB1B1"; font.pixelSize: 10
                }
            }
        }
    }
}
