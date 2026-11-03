pragma ComponentBehavior: Bound
import qs
import qs.services
import QtQuick
import QtQuick.Layouts

/** Standalone Sword Art Online: Aincrad HUD launcher, drawn from scratch. */
Item {
    id: menu
    property var host
    signal closed
    readonly property color ink: "#050A14"
    readonly property color cyan: "#55DDF5"
    readonly property color cyanDim: "#2B8198"
    readonly property color crimson: "#FF526F"
    readonly property color text: "#EAF7FF"
    readonly property color muted: "#8BAABD"
    property real appear: 0
    property bool closing: false
    property string page: "home"
    property string query: ""
    readonly property var appList: !host ? [] : (query === "" ? host.apps() : AppSearch.fuzzyQuery(query))
    readonly property var shownApps: page === "apps" ? appList : appList.slice(0, 8)
    onQueryChanged: LauncherSearch.query = query

    function open() {
        closeAnim.stop(); closing = false; page = "home"; query = ""; appear = 0;
        forceActiveFocus(); openAnim.restart();
    }
    function close() {
        if (closing) return;
        closing = true; openAnim.stop(); closeAnim.start();
    }
    function launchFirst() {
        if (query !== "" && LauncherSearch.results.length > 0)
            host.runResult(LauncherSearch.results[0]);
        else if (shownApps.length > 0)
            host.launchEntry(shownApps[0]);
    }
    NumberAnimation { id: openAnim; target: menu; property: "appear"; to: 1; duration: 280; easing.type: Easing.OutCubic }
    SequentialAnimation {
        id: closeAnim
        NumberAnimation { target: menu; property: "appear"; to: 0; duration: 180; easing.type: Easing.InCubic }
        ScriptAction { script: menu.closed() }
    }
    focus: true
    Keys.onPressed: event => {
        if (event.key === Qt.Key_Escape) {
            if (menu.query !== "") menu.query = "";
            else menu.host.dismiss();
            event.accepted = true;
        } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
            menu.launchFirst(); event.accepted = true;
        }
    }

    Rectangle { anchors.fill: parent; color: "#B8030914"; opacity: menu.appear }
    Rectangle {
        id: frame
        width: Math.min(parent.width * 0.92, 1240)
        height: Math.min(parent.height * 0.86, 760)
        anchors.centerIn: parent
        radius: 18
        color: menu.ink
        border.width: 1.5
        border.color: Qt.rgba(menu.cyan.r, menu.cyan.g, menu.cyan.b, 0.72)
        opacity: menu.appear
        scale: 0.96 + menu.appear * 0.04
        clip: true
        Behavior on scale { NumberAnimation { duration: 260; easing.type: Easing.OutCubic } }
        MouseArea { anchors.fill: parent; onClicked: {} }
        Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; height: 3; color: menu.cyan }

        RowLayout {
            id: header
            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
            anchors.margins: 26; height: 54; spacing: 18
            ColumnLayout {
                spacing: 2
                Text { text: "AINCRAD"; color: menu.cyan; font.pixelSize: 20; font.weight: Font.Bold; font.letterSpacing: 4 }
                Text { text: "SYSTEM MENU  /  FLOOR 01"; color: menu.muted; font.pixelSize: 10; font.letterSpacing: 2 }
            }
            Item { Layout.fillWidth: true }
            Text { text: "PLAYER SESSION  /  " + DateTime.time; color: menu.text; font.pixelSize: 12; font.family: "monospace" }
            Rectangle {
                Layout.preferredWidth: 76; Layout.preferredHeight: 32; radius: 5
                color: "#132B3E"; border.color: menu.cyanDim
                Text { anchors.centerIn: parent; text: "ESC"; color: menu.cyan; font.pixelSize: 11; font.bold: true }
                MouseArea { anchors.fill: parent; onClicked: menu.host.dismiss() }
            }
        }
        Rectangle { anchors.top: header.bottom; anchors.left: parent.left; anchors.right: parent.right; height: 1; color: "#21435A" }

        RowLayout {
            anchors.top: header.bottom; anchors.bottom: footer.top
            anchors.left: parent.left; anchors.right: parent.right
            anchors.margins: 24; anchors.topMargin: 22; anchors.bottomMargin: 18; spacing: 20

            ColumnLayout {
                Layout.preferredWidth: 176; Layout.fillHeight: true; spacing: 12
                Text { text: "NAVIGATION"; color: menu.muted; font.pixelSize: 10; font.letterSpacing: 2 }
                Repeater {
                    model: [{id:"home",label:"HOME",mark:"⌂"},{id:"apps",label:"APPLICATIONS",mark:"▦"},{id:"system",label:"SYSTEM",mark:"◇"}]
                    delegate: Rectangle {
                        required property var modelData
                        Layout.fillWidth: true; height: 48; radius: 6
                        color: menu.page === modelData.id ? "#12364A" : "transparent"
                        border.width: menu.page === modelData.id ? 1 : 0; border.color: menu.cyanDim
                        Row {
                            anchors.fill: parent; anchors.leftMargin: 12; spacing: 12
                            Text { anchors.verticalCenter: parent.verticalCenter; text: modelData.mark; color: menu.page === modelData.id ? menu.cyan : menu.muted; font.pixelSize: 20 }
                            Text { anchors.verticalCenter: parent.verticalCenter; text: modelData.label; color: menu.page === modelData.id ? menu.text : menu.muted; font.pixelSize: 10; font.letterSpacing: 1 }
                        }
                        MouseArea { anchors.fill: parent; onClicked: menu.page = modelData.id }
                    }
                }
                Item { Layout.fillHeight: true }
                Rectangle {
                    Layout.fillWidth: true; height: 104; radius: 7; color: "#091B2A"; border.color: "#1D3A50"
                    Column {
                        anchors.fill: parent; anchors.margins: 12; spacing: 7
                        Text { text: "NETWORK"; color: menu.muted; font.pixelSize: 9; font.letterSpacing: 2 }
                        Text { text: "CONNECTED"; color: "#63E6A5"; font.pixelSize: 11; font.bold: true }
                        Text { text: "AINCRAD GATEWAY"; color: menu.muted; font.pixelSize: 9; font.family: "monospace" }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true; Layout.fillHeight: true; color: "#071321"; radius: 9; border.color: "#19364B"
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 20; spacing: 16
                    RowLayout {
                        Layout.fillWidth: true
                        ColumnLayout {
                            spacing: 3
                            Text { text: menu.page === "apps" ? "APPLICATION INDEX" : menu.page === "system" ? "SYSTEM STATUS" : "WELCOME BACK, PLAYER"; color: menu.text; font.pixelSize: 20; font.weight: Font.DemiBold; font.letterSpacing: 1 }
                            Text { text: menu.page === "apps" ? "Select an installed application" : "Your virtual environment is ready"; color: menu.muted; font.pixelSize: 11 }
                        }
                        Item { Layout.fillWidth: true }
                        Text { text: "01 / 100"; color: menu.cyan; font.pixelSize: 11; font.family: "monospace" }
                    }
                    Rectangle {
                        Layout.fillWidth: true; height: 46; radius: 5; color: "#0C2032"; border.width: 1; border.color: menu.cyanDim
                        RowLayout {
                            anchors.fill: parent; anchors.leftMargin: 14; anchors.rightMargin: 14; spacing: 10
                            Text { text: "⌕"; color: menu.cyan; font.pixelSize: 22 }
                            TextInput {
                                id: search; Layout.fillWidth: true; color: menu.text; selectionColor: menu.cyan; selectedTextColor: menu.ink
                                font.pixelSize: 13; font.family: "monospace"; clip: true; focus: true
                                text: menu.query; onTextChanged: menu.query = text; onAccepted: menu.launchFirst()
                                Text {
                                    anchors.fill: parent; verticalAlignment: Text.AlignVCenter
                                    text: "SEARCH APPS  /  COMMANDS  /  CALCULATIONS"; color: menu.muted; font: search.font
                                    visible: search.text.length === 0
                                }
                            }
                            Text { text: "ENTER"; color: menu.cyan; font.pixelSize: 9; font.letterSpacing: 1 }
                        }
                    }
                    Text { text: menu.query !== "" ? "MATCHING RESULTS" : menu.page === "apps" ? "ALL APPLICATIONS" : "QUICK ACCESS"; color: menu.muted; font.pixelSize: 9; font.letterSpacing: 2 }
                    GridView {
                        id: appGrid; Layout.fillWidth: true; Layout.fillHeight: true
                        cellWidth: Math.max(130, width / 3); cellHeight: 104; clip: true; model: menu.shownApps
                        delegate: Rectangle {
                            required property var modelData
                            width: appGrid.cellWidth - 10; height: appGrid.cellHeight - 10; radius: 7
                            color: appMouse.containsMouse ? "#14334A" : "#0B1D2D"
                            border.width: appMouse.containsMouse ? 1.5 : 1; border.color: appMouse.containsMouse ? menu.cyan : "#1A3549"
                            Column {
                                anchors.fill: parent; anchors.margins: 12; spacing: 8
                                Rectangle {
                                    width: 30; height: 30; radius: 6; color: "#12394A"
                                    Text { anchors.centerIn: parent; text: String(modelData.name ?? "?").slice(0,1).toUpperCase(); color: menu.cyan; font.pixelSize: 16; font.bold: true }
                                }
                                Text { width: parent.width; text: modelData.name ?? "Application"; color: menu.text; font.pixelSize: 11; elide: Text.ElideRight }
                            }
                            MouseArea { id: appMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: menu.host.launchEntry(modelData) }
                        }
                    }
                }
            }

            ColumnLayout {
                Layout.preferredWidth: 210; Layout.fillHeight: true; spacing: 14
                Text { text: "PLAYER STATUS"; color: menu.cyan; font.pixelSize: 10; font.letterSpacing: 2 }
                Rectangle {
                    Layout.fillWidth: true; height: 142; radius: 8; color: "#0A1C2C"; border.color: "#1A3B52"
                    Column {
                        anchors.fill: parent; anchors.margins: 14; spacing: 10
                        Text { text: "HP  /  SYSTEM POWER"; color: menu.muted; font.pixelSize: 9; font.letterSpacing: 1 }
                        Text { text: Battery.available ? Math.round(Battery.percentage * 100) + "%" : "ONLINE"; color: menu.text; font.pixelSize: 28; font.bold: true }
                        Rectangle {
                            width: parent.width; height: 7; radius: 4; color: "#20364A"
                            Rectangle { width: parent.width * (Battery.available ? Math.max(0, Math.min(1, Battery.percentage)) : 1); height: parent.height; radius: 4; color: menu.cyan }
                        }
                        Text { text: "PLAYER: LOCAL SESSION"; color: menu.muted; font.pixelSize: 9; font.family: "monospace" }
                    }
                }
                Rectangle {
                    Layout.fillWidth: true; height: 118; radius: 8; color: "#0A1C2C"; border.color: "#1A3B52"
                    Column {
                        anchors.fill: parent; anchors.margins: 14; spacing: 8
                        Text { text: "ALERT STATUS"; color: menu.muted; font.pixelSize: 9; font.letterSpacing: 1 }
                        Row {
                            spacing: 7
                            Rectangle { width: 7; height: 7; radius: 4; color: "#63E6A5"; anchors.verticalCenter: parent.verticalCenter }
                            Text { text: "NO ACTIVE ALERTS"; color: "#A8EFC8"; font.pixelSize: 10 }
                        }
                        Text { text: "MONITOR: " + (Hyprland.focusedMonitor?.name ?? "ACTIVE"); color: menu.muted; font.pixelSize: 9; font.family: "monospace" }
                    }
                }
                Rectangle {
                    Layout.fillWidth: true; height: 90; radius: 8; color: "#251421"; border.color: "#6B2940"
                    Column {
                        anchors.fill: parent; anchors.margins: 14; spacing: 6
                        Text { text: "HEALTH SIGNAL"; color: menu.crimson; font.pixelSize: 9; font.letterSpacing: 1 }
                        Text { text: "100%"; color: menu.text; font.pixelSize: 23; font.bold: true }
                        Text { text: "VIRTUAL BODY INTEGRITY"; color: menu.muted; font.pixelSize: 8 }
                    }
                }
                Item { Layout.fillHeight: true }
                Text { text: "A SAFE RETURN IS NOT GUARANTEED."; color: menu.muted; font.pixelSize: 8; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            }
        }

        Rectangle {
            id: footer
            anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
            height: 34; color: "#07111D"
            Text { anchors.left: parent.left; anchors.leftMargin: 24; anchors.verticalCenter: parent.verticalCenter; text: "NEXUS SYSTEM INTERFACE  //  AINCRAD ONLINE"; color: menu.cyanDim; font.pixelSize: 9; font.letterSpacing: 1 }
            Text { anchors.right: parent.right; anchors.rightMargin: 24; anchors.verticalCenter: parent.verticalCenter; text: "ESC  CLOSE"; color: menu.muted; font.pixelSize: 9; font.family: "monospace" }
        }
    }
}