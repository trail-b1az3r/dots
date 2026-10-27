pragma ComponentBehavior: Bound

import qs
import qs.services
import qs.modules.common
import qs.modules.common.functions
import qs.modules.common.models
import qs.modules.common.widgets
import QtQuick
import QtQuick.Shapes
import Quickshell
import Quickshell.Io
import Quickshell.Widgets

/**
 * After ICEY's app picker: a phone, slid up from the bottom of the screen. Its home screen has four apps: Apps (every
 * app, with a search), Auto (type anything: an app opens, a sum is worked out, a command runs, whatever LauncherSearch
 * finds), Theme (the Halcyon themes, tap one to wear it) and Calculator. Typing on the home screen goes straight to
 * Auto. Esc goes back home, and from home puts the phone away.
 */
Item {
    id: phone

    property var host
    signal closed

    readonly property color hull: "#080D18"
    readonly property color glass: "#0E1524"
    readonly property color cyan: "#5CD6F2"
    readonly property color amber: "#FFD86B"
    readonly property color text: "#E4ECF7"
    readonly property color dim: "#8794B0"

    readonly property real phoneH: Math.min(height * 0.84, 860)
    readonly property real phoneW: phoneH * 0.5

    // home, apps, auto, theme or calc.
    property string page: "home"
    property string query: ""
    onQueryChanged: LauncherSearch.query = page === "auto" ? query : ""

    function go(next) {
        query = "";
        page = next;
        if (next === "theme")
            themeProc.running = true;
    }

    // ── Sliding up and away ──────────────────────────────────────────────────
    property real appear: 0
    property bool closing: false
    Component.onCompleted: openAnim.start()
    function close() {
        if (closing)
            return;
        closing = true;
        openAnim.stop();
        closeAnim.start();
    }
    NumberAnimation { id: openAnim; target: phone; property: "appear"; from: 0; to: 1; duration: 460; easing.type: Easing.OutBack; easing.overshoot: 1.1 }
    SequentialAnimation {
        id: closeAnim
        NumberAnimation { target: phone; property: "appear"; to: 0; duration: 300; easing.type: Easing.InCubic }
        ScriptAction { script: phone.closed() }
    }

    // ── Keys ─────────────────────────────────────────────────────────────────
    focus: true
    Keys.onPressed: event => {
        if (event.key === Qt.Key_Escape) {
            if (phone.query !== "")
                phone.query = "";
            else if (phone.page !== "home")
                phone.go("home");
            else
                phone.host.dismiss();
        } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
            phone.enter();
        } else if (event.key === Qt.Key_Backspace) {
            phone.query = phone.query.slice(0, -1);
        } else if (event.text.length === 1 && event.text >= " ") {
            if (phone.page === "home" || phone.page === "theme")
                phone.go("auto");
            phone.query += event.text;
        } else {
            return;
        }
        event.accepted = true;
    }
    function enter() {
        if (page === "apps" && appList.length > 0)
            host.launchEntry(appList[0]);
        else if (page === "auto" && LauncherSearch.results.length > 0)
            host.runResult(LauncherSearch.results[0]);
        else if (page === "calc")
            calc.equals();
    }

    readonly property var appList: page !== "apps" ? [] : query === "" ? (host ? host.apps() : []) : AppSearch.fuzzyQuery(query)

    // ── The phone ────────────────────────────────────────────────────────────
    Item {
        id: body
        width: phone.phoneW
        height: phone.phoneH
        anchors.horizontalCenter: parent.horizontalCenter
        y: (phone.height - height) / 2 + (1 - phone.appear) * (phone.height * 0.7)
        opacity: Math.min(1, phone.appear * 1.6)
        transform: Rotation {
            origin.x: body.width / 2
            origin.y: body.height
            axis { x: 1; y: 0; z: 0 }
            angle: (1 - phone.appear) * 28
        }

        MouseArea { anchors.fill: parent }    // clicks on the phone stay on the phone

        // The hull: a chamfered slab, a cyan rim, HUD brackets at the corners.
        Shape {
            anchors.fill: parent
            anchors.margins: -14
            preferredRendererType: Shape.CurveRenderer
            ShapePath {
                strokeWidth: 2
                strokeColor: phone.cyan
                fillColor: phone.hull
                joinStyle: ShapePath.MiterJoin
                PathSvg { path: phone.chamfer(body.width + 28, body.height + 28, 34) }
            }
            ShapePath {
                strokeWidth: 3
                strokeColor: phone.cyan
                fillColor: "transparent"
                capStyle: ShapePath.FlatCap
                PathSvg { path: phone.brackets(body.width + 28, body.height + 28, 34, 28) }
            }
        }
        // The screen.
        Rectangle {
            id: screenRect
            anchors.fill: parent
            anchors.margins: 6
            radius: 14
            color: phone.glass
            clip: true
            border.width: 1
            border.color: Qt.rgba(0.36, 0.84, 0.95, 0.25)

            // Scan lines, faint.
            Shape {
                anchors.fill: parent
                opacity: 0.07
                ShapePath {
                    strokeWidth: 1
                    strokeColor: phone.cyan
                    fillColor: "transparent"
                    PathSvg {
                        path: {
                            let d = "";
                            for (let y = 4; y < screenRect.height; y += 6)
                                d += `M 0 ${y} L ${screenRect.width} ${y} `;
                            return d;
                        }
                    }
                }
            }

            // Status bar: the time, a notch, the battery.
            Item {
                id: status
                width: parent.width
                height: 34
                StyledText {
                    x: 18
                    anchors.verticalCenter: parent.verticalCenter
                    text: DateTime.time
                    color: phone.text
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                    font.family: Appearance.font.family.monospace
                }
                Rectangle {
                    anchors.centerIn: parent
                    width: 86
                    height: 18
                    radius: 9
                    color: "black"
                    Rectangle { x: parent.width - 18; anchors.verticalCenter: parent.verticalCenter; width: 7; height: 7; radius: 4; color: phone.cyan; opacity: 0.6 }
                }
                StyledText {
                    anchors.right: parent.right
                    anchors.rightMargin: 18
                    anchors.verticalCenter: parent.verticalCenter
                    text: Battery.available ? `${Math.round(Battery.percentage * 100)}%` : "ICEY"
                    color: phone.cyan
                    font.pixelSize: 12
                    font.family: Appearance.font.family.monospace
                }
            }

            // The pages, zooming in from the app tapped and back out to home.
            Item {
                id: pages
                anchors.fill: parent
                anchors.topMargin: status.height
                anchors.bottomMargin: 30

                Screen { name: "home"; HomePage { anchors.fill: parent } }
                Screen { name: "apps"; AppsPage { anchors.fill: parent } }
                Screen { name: "auto"; AutoPage { anchors.fill: parent } }
                Screen { name: "theme"; ThemePage { anchors.fill: parent } }
                Screen { name: "calc"; CalcPage { id: calc; anchors.fill: parent } }
            }

            // The home bar: a tap goes home, from home puts the phone away.
            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 10
                width: homeBar.containsMouse ? 140 : 110
                height: 5
                radius: 3
                color: phone.cyan
                opacity: 0.8
                Behavior on width { NumberAnimation { duration: 160 } }
                MouseArea {
                    id: homeBar
                    anchors.fill: parent
                    anchors.margins: -12
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: phone.page === "home" ? phone.host.dismiss() : phone.go("home")
                }
            }
        }
    }

    /** The hull's outline: a w x h rectangle with corners cut off c deep. */
    function chamfer(w, h, c) {
        return `M ${c} 0 L ${w - c} 0 L ${w} ${c} L ${w} ${h - c} L ${w - c} ${h} L ${c} ${h} L 0 ${h - c} L 0 ${c} Z`;
    }
    /** Brackets along the cut corners, l long, set just outside them. */
    function brackets(w, h, c, l) {
        const o = -6;
        return `M ${o} ${c + l} L ${o} ${c - 2} L ${c - 2} ${o} L ${c + l} ${o} `
             + `M ${w - c - l} ${o} L ${w - c + 2} ${o} L ${w - o} ${c - 2} L ${w - o} ${c + l} `
             + `M ${w - o} ${h - c - l} L ${w - o} ${h - c + 2} L ${w - c + 2} ${h - o} L ${w - c - l} ${h - o} `
             + `M ${c + l} ${h - o} L ${c - 2} ${h - o} L ${o} ${h - c + 2} L ${o} ${h - c - l}`;
    }

    // ── A page of the phone: fades and zooms in when it is the one showing ────
    component Screen: Item {
        id: screen
        property string name
        readonly property bool current: phone.page === screen.name
        anchors.fill: parent
        opacity: current ? 1 : 0
        scale: current ? 1 : (screen.name === "home" ? 0.9 : 1.12)
        visible: opacity > 0
        enabled: current
        Behavior on opacity { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
        Behavior on scale { NumberAnimation { duration: 280; easing.type: Easing.OutCubic } }
    }

    // ── Pieces the pages share ───────────────────────────────────────────────
    component Header: Item {
        id: header
        property string title
        width: parent?.width ?? 0
        height: 44
        Row {
            x: 14
            anchors.verticalCenter: parent.verticalCenter
            spacing: 8
            StyledText {
                text: "‹"
                color: phone.cyan
                font.pixelSize: 26
                MouseArea {
                    anchors.fill: parent
                    anchors.margins: -8
                    cursorShape: Qt.PointingHandCursor
                    onClicked: phone.go("home")
                }
            }
            StyledText {
                anchors.verticalCenter: parent.verticalCenter
                text: header.title.toUpperCase()
                color: phone.text
                font.pixelSize: 16
                font.weight: Font.Bold
                font.letterSpacing: 3
            }
        }
    }
    component Field: Rectangle {
        id: field
        property string placeholder
        width: parent?.width ?? 0
        height: 40
        radius: 4
        color: Qt.rgba(0.36, 0.84, 0.95, 0.06)
        border.width: 1.5
        border.color: phone.cyan
        StyledText {
            x: 12
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width - 24
            elide: Text.ElideLeft
            text: phone.query === "" ? field.placeholder : phone.query + "▍"
            color: phone.query === "" ? phone.dim : phone.text
            font.pixelSize: 14
            font.family: Appearance.font.family.monospace
        }
    }

    // ── Home: the clock, and four apps ───────────────────────────────────────
    component HomePage: Item {
        Column {
            anchors.horizontalCenter: parent.horizontalCenter
            y: parent.height * 0.08
            spacing: 4
            StyledText {
                anchors.horizontalCenter: parent.horizontalCenter
                text: DateTime.time
                color: phone.text
                font.pixelSize: Math.round(phone.phoneW * 0.2)
                font.weight: Font.Light
                font.family: Appearance.font.family.monospace
            }
            StyledText {
                anchors.horizontalCenter: parent.horizontalCenter
                text: DateTime.date
                color: phone.cyan
                font.pixelSize: 13
                font.letterSpacing: 2
            }
        }
        Grid {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: parent.height * 0.1
            columns: 2
            spacing: 22
            Repeater {
                model: [
                    { page: "apps", icon: "apps", label: Translation.tr("Apps") },
                    { page: "auto", icon: "bolt", label: Translation.tr("Auto") },
                    { page: "theme", icon: "palette", label: Translation.tr("Theme") },
                    { page: "calc", icon: "calculate", label: Translation.tr("Calculator") }
                ]
                delegate: Item {
                    id: tile
                    required property var modelData
                    width: phone.phoneW * 0.32
                    height: width + 24
                    Shape {
                        id: hex
                        width: tile.width
                        height: tile.width
                        scale: tileArea.pressed ? 0.92 : tileArea.containsMouse ? 1.05 : 1
                        Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutBack } }
                        preferredRendererType: Shape.CurveRenderer
                        ShapePath {
                            strokeWidth: 2
                            strokeColor: tileArea.containsMouse ? phone.amber : phone.cyan
                            fillColor: Qt.rgba(0.36, 0.84, 0.95, tileArea.containsMouse ? 0.18 : 0.08)
                            joinStyle: ShapePath.MiterJoin
                            PathSvg {
                                path: {
                                    const r = hex.width / 2 - 2, c = hex.width / 2;
                                    let d = "";
                                    for (let i = 0; i < 6; i++) {
                                        const a = Math.PI / 3 * i;
                                        d += `${i === 0 ? "M" : "L"} ${c + r * Math.cos(a)} ${c + r * Math.sin(a)} `;
                                    }
                                    return d + "Z";
                                }
                            }
                        }
                        MaterialSymbol {
                            anchors.centerIn: parent
                            text: tile.modelData.icon
                            iconSize: Math.round(hex.width * 0.36)
                            color: tileArea.containsMouse ? phone.amber : phone.cyan
                        }
                    }
                    StyledText {
                        anchors.bottom: parent.bottom
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: tile.modelData.label
                        color: phone.text
                        font.pixelSize: 12
                        font.letterSpacing: 1
                    }
                    MouseArea {
                        id: tileArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: phone.go(tile.modelData.page)
                    }
                }
            }
        }
    }

    // ── Apps: a search and every app, four across ────────────────────────────
    component AppsPage: Item {
        Header { id: appsHeader; title: Translation.tr("Apps") }
        Field {
            id: appsField
            anchors.top: appsHeader.bottom
            x: 14
            width: parent.width - 28
            placeholder: Translation.tr("type to find an app")
        }
        GridView {
            id: appGrid
            anchors.top: appsField.bottom
            anchors.topMargin: 12
            anchors.bottom: parent.bottom
            x: 8
            width: parent.width - 16
            clip: true
            cellWidth: width / 4
            cellHeight: cellWidth * 0.5 + 44
            model: phone.appList
            delegate: Item {
                id: appCell
                required property var modelData
                required property int index
                width: appGrid.cellWidth
                height: appGrid.cellHeight
                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 3
                    radius: 6
                    color: Qt.rgba(0.36, 0.84, 0.95, appArea.containsMouse ? 0.14 : 0)
                    border.width: appCell.index === 0 && phone.query !== "" ? 1.5 : 0
                    border.color: phone.amber
                }
                IconImage {
                    id: appIcon
                    anchors.horizontalCenter: parent.horizontalCenter
                    y: 10
                    implicitSize: Math.round(appGrid.cellWidth * 0.5)
                    source: AppSearch.iconSource(appCell.modelData?.icon ?? "")
                }
                StyledText {
                    anchors.top: appIcon.bottom
                    anchors.topMargin: 6
                    width: parent.width - 6
                    x: 3
                    horizontalAlignment: Text.AlignHCenter
                    elide: Text.ElideRight
                    text: appCell.modelData?.name ?? ""
                    color: phone.text
                    font.pixelSize: 11
                }
                MouseArea {
                    id: appArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: phone.host.launchEntry(appCell.modelData)
                }
            }
        }
    }

    // ── Auto: type anything, and the phone works out what you meant ──────────
    component AutoPage: Item {
        Header { id: autoHeader; title: Translation.tr("Auto") }
        Field {
            id: autoField
            anchors.top: autoHeader.bottom
            x: 14
            width: parent.width - 28
            placeholder: Translation.tr("an app, a sum, a command…")
        }
        ListView {
            id: resultList
            anchors.top: autoField.bottom
            anchors.topMargin: 12
            anchors.bottom: parent.bottom
            x: 10
            width: parent.width - 20
            clip: true
            spacing: 6
            model: phone.query === "" ? [] : LauncherSearch.results.slice(0, 30)
            delegate: Rectangle {
                id: row
                required property var modelData
                required property int index
                width: resultList.width
                height: 52
                radius: 4
                color: Qt.rgba(0.36, 0.84, 0.95, rowArea.containsMouse ? 0.16 : 0.05)
                border.width: row.index === 0 ? 1.5 : 1
                border.color: row.index === 0 ? phone.amber : Qt.rgba(0.36, 0.84, 0.95, 0.3)
                Loader {
                    id: rowIcon
                    x: 10
                    anchors.verticalCenter: parent.verticalCenter
                    width: 30
                    height: 30
                    sourceComponent: row.modelData.iconType === LauncherSearchResult.IconType.System ? sysIcon : symIcon
                    Component { id: sysIcon; IconImage { implicitSize: 30; source: Quickshell.iconPath(row.modelData.iconName, "application-x-executable") } }
                    Component { id: symIcon; MaterialSymbol { text: row.modelData.iconName || "bolt"; iconSize: 24; color: phone.cyan } }
                }
                Column {
                    anchors.left: rowIcon.right
                    anchors.leftMargin: 10
                    anchors.right: chip.left
                    anchors.rightMargin: 8
                    anchors.verticalCenter: parent.verticalCenter
                    StyledText {
                        width: parent.width
                        elide: Text.ElideRight
                        text: row.modelData.name
                        color: phone.text
                        font.pixelSize: 13
                    }
                    StyledText {
                        text: row.index === 0 ? Translation.tr("↵ %1").arg(row.modelData.verb) : row.modelData.verb
                        color: row.index === 0 ? phone.amber : phone.dim
                        font.pixelSize: 11
                    }
                }
                // What kind of thing it is: app, math, command, web...
                Rectangle {
                    id: chip
                    anchors.right: parent.right
                    anchors.rightMargin: 10
                    anchors.verticalCenter: parent.verticalCenter
                    width: chipText.implicitWidth + 12
                    height: 20
                    color: "transparent"
                    border.width: 1
                    border.color: phone.cyan
                    StyledText {
                        id: chipText
                        anchors.centerIn: parent
                        text: (row.modelData.type ?? "").toUpperCase()
                        color: phone.cyan
                        font.pixelSize: 9
                        font.letterSpacing: 1
                    }
                }
                MouseArea {
                    id: rowArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: phone.host.runResult(row.modelData)
                }
            }
        }
        StyledText {
            anchors.centerIn: resultList
            visible: phone.query === ""
            width: resultList.width - 20
            wrapMode: Text.Wrap
            horizontalAlignment: Text.AlignHCenter
            text: Translation.tr("Type: firefox opens it, 12*7 works it out, a command runs it.")
            color: phone.dim
            font.pixelSize: 13
        }
    }

    // ── Theme: the Halcyon themes as cards in their own colours ──────────────
    property var themes: []
    readonly property string themeTool: `${FileUtils.trimFileProtocol(Directories.config)}/hypr/hyprland/halcyon/halcyon-theme`
    Process {
        id: themeProc
        command: [phone.themeTool, "list", "--json"]
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    phone.themes = JSON.parse(this.text).themes ?? [];
                } catch (error) {
                    phone.themes = [];
                }
            }
        }
    }
    component ThemePage: Item {
        Header { id: themeHeader; title: Translation.tr("Theme") }
        ListView {
            id: themeList
            anchors.top: themeHeader.bottom
            anchors.bottom: parent.bottom
            x: 12
            width: parent.width - 24
            clip: true
            spacing: 10
            model: phone.themes
            delegate: Rectangle {
                id: card
                required property var modelData
                readonly property var c: modelData.colors ?? {}
                width: themeList.width
                height: 64
                radius: 4
                color: c.background ?? phone.hull
                border.width: modelData.active ? 2 : 1
                border.color: modelData.active ? phone.amber : (cardArea.containsMouse ? phone.cyan : Qt.rgba(0.36, 0.84, 0.95, 0.35))
                Row {
                    x: 12
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 5
                    Repeater {
                        model: [card.c.primary, card.c.secondary, card.c.tertiary]
                        delegate: Rectangle {
                            required property var modelData
                            width: 14
                            height: 14
                            radius: 7
                            color: modelData ?? "gray"
                        }
                    }
                }
                StyledText {
                    x: 76
                    anchors.verticalCenter: parent.verticalCenter
                    width: parent.width - 86
                    elide: Text.ElideRight
                    text: card.modelData.name + (card.modelData.active ? "  ·  " + Translation.tr("on") : "")
                    color: card.c.on_background ?? phone.text
                    font.pixelSize: 14
                    font.weight: Font.DemiBold
                }
                MouseArea {
                    id: cardArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        Quickshell.execDetached([phone.themeTool, "apply", card.modelData.id]);
                        phone.host.dismiss();
                    }
                }
            }
        }
    }

    // ── Calculator: a keypad, worked out by qalc ─────────────────────────────
    component CalcPage: Item {
        id: calcPage
        property string answer: ""
        function equals() {
            if (phone.query.trim() === "")
                return;
            qalc.command = ["bash", "-c", "command -v qalc >/dev/null || { echo \"$2\"; exit; }; qalc -t \"$1\"", "_", phone.query, Translation.tr("qalc is not installed")];
            qalc.running = true;
        }
        function press(key) {
            if (key === "C") {
                phone.query = "";
                calcPage.answer = "";
            } else if (key === "⌫") {
                phone.query = phone.query.slice(0, -1);
            } else if (key === "=") {
                calcPage.equals();
            } else {
                phone.query += key;
            }
        }
        Process {
            id: qalc
            stdout: StdioCollector {
                onStreamFinished: calcPage.answer = this.text.trim()
            }
        }
        Header { id: calcHeader; title: Translation.tr("Calculator") }
        // The display: what you typed, and the answer under it.
        Rectangle {
            id: display
            anchors.top: calcHeader.bottom
            x: 14
            width: parent.width - 28
            height: 96
            radius: 4
            color: Qt.rgba(0.36, 0.84, 0.95, 0.06)
            border.width: 1.5
            border.color: phone.cyan
            StyledText {
                anchors.right: parent.right
                anchors.rightMargin: 12
                y: 12
                width: parent.width - 24
                horizontalAlignment: Text.AlignRight
                elide: Text.ElideLeft
                text: phone.query === "" ? "0" : phone.query
                color: phone.dim
                font.pixelSize: 16
                font.family: Appearance.font.family.monospace
            }
            StyledText {
                anchors.right: parent.right
                anchors.rightMargin: 12
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 10
                width: parent.width - 24
                horizontalAlignment: Text.AlignRight
                elide: Text.ElideLeft
                text: calcPage.answer
                color: phone.amber
                font.pixelSize: 30
                fontSizeMode: Text.HorizontalFit
                minimumPixelSize: 12
                font.family: Appearance.font.family.monospace
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: Quickshell.clipboardText = calcPage.answer
                }
            }
        }
        Grid {
            id: keypad
            anchors.top: display.bottom
            anchors.topMargin: 14
            anchors.bottom: parent.bottom
            x: 14
            width: parent.width - 28
            columns: 4
            spacing: 8
            readonly property real keyW: (width - 3 * spacing) / 4
            readonly property real keyH: Math.min(keyW * 0.8, (height - 4 * spacing) / 5)
            Repeater {
                model: ["C", "(", ")", "⌫", "7", "8", "9", "/", "4", "5", "6", "*", "1", "2", "3", "-", "0", ".", "=", "+"]
                delegate: Rectangle {
                    id: key
                    required property string modelData
                    readonly property bool op: "/*-+=()C⌫".includes(modelData)
                    width: keypad.keyW
                    height: keypad.keyH
                    radius: 4
                    color: key.modelData === "=" ? phone.cyan : Qt.rgba(0.36, 0.84, 0.95, keyArea.pressed ? 0.3 : keyArea.containsMouse ? 0.16 : 0.07)
                    border.width: 1
                    border.color: key.op ? phone.cyan : Qt.rgba(0.36, 0.84, 0.95, 0.3)
                    scale: keyArea.pressed ? 0.94 : 1
                    Behavior on scale { NumberAnimation { duration: 90 } }
                    StyledText {
                        anchors.centerIn: parent
                        text: key.modelData
                        color: key.modelData === "=" ? phone.hull : key.op ? phone.cyan : phone.text
                        font.pixelSize: 18
                        font.family: Appearance.font.family.monospace
                    }
                    MouseArea {
                        id: keyArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: calcPage.press(key.modelData)
                    }
                }
            }
        }
    }
}
