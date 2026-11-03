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
import Quickshell.Bluetooth
import Quickshell.Hyprland
import Quickshell.Widgets

/**
 * Sword Art Online's main menu, for the Sword Art Online theme, drawn from scratch: a column of round white buttons
 * that drop in one after another, and beside it the panel of the one chosen, unfolding from it on a pointer. The
 * player's card stands to the left: name, level, HP and MP bars and the time, as on the game's HUD.
 *
 *   Status    the player: HP is the battery (or free memory without one), MP the free memory, STA the idle CPU,
 *             the floor is the workspace, time played the uptime
 *   Items     the apps, in categories; a category opens its apps in a second panel. Typing searches instead:
 *             an app, a sum, a command, whatever LauncherSearch finds
 *   Party     the open windows; choose one to go to it
 *   Map       the floors (workspaces) and how many windows each has; choose one to go there
 *   Messages  the notifications; choose one to dismiss it, or clear them all
 *   System    Wi-Fi, Bluetooth, do not disturb, Settings, lock, and Log Out, which asks first the way the game
 *             does: a dialog with a round blue ○ and a red ✕
 *
 * Keys: up and down move, right or Enter goes into a panel (or runs the row), left comes back out, Esc steps back
 * and from the column puts the menu away.
 */
Item {
    id: menu

    property var host
    signal closed

    // The game's menu: white plates, grey text, orange for what is chosen.
    readonly property color plate: "#F4F6F8"
    readonly property color plateEdge: "#C9D0D8"
    readonly property color rowLine: "#DFE4EA"
    readonly property color ink: "#4A525C"
    readonly property color inkDim: "#8A939D"
    readonly property color orange: "#F5A43B"
    readonly property color orangeLight: "#FFC77A"
    readonly property color crimson: "#E0464E"
    readonly property color okBlue: "#3B8FE0"
    readonly property string font: Appearance.font.family.main

    // ── What is open ─────────────────────────────────────────────────────────
    readonly property var buttons: [
        { id: "status", icon: "person", label: Translation.tr("Status") },
        { id: "items", icon: "swords", label: Translation.tr("Items") },
        { id: "party", icon: "group", label: Translation.tr("Party") },
        { id: "map", icon: "explore", label: Translation.tr("Map") },
        { id: "messages", icon: "mail", label: Translation.tr("Messages") },
        { id: "system", icon: "settings", label: Translation.tr("System") }
    ]
    property int selected: 1
    readonly property string section: buttons[selected]?.id ?? ""
    // Where the keys are: 0 the column, 1 the panel, 2 the second panel (Items' apps).
    property int depth: 0
    property int row: 0
    property int subRow: 0
    property string category: ""
    property string query: ""
    property bool confirmLogout: false
    onQueryChanged: {
        LauncherSearch.query = query;
        if (query !== "") {
            selected = 1;
            category = "";
            depth = 1;
            row = 0;
        }
    }
    onSelectedChanged: {
        row = 0;
        subRow = 0;
        category = "";
        unfold.restart();
    }

    // ── Opening and closing: the buttons drop in, in turn, and rise away ─────
    property real appear: 0
    property bool closing: false
    function open() {
        closeAnim.stop();
        closing = false;
        selected = 1;
        depth = 0;
        query = "";
        category = "";
        confirmLogout = false;
        appear = 0;
        forceActiveFocus();
        openAnim.restart();
        unfold.restart();
    }
    function close() {
        if (closing)
            return;
        closing = true;
        openAnim.stop();
        closeAnim.start();
    }
    NumberAnimation { id: openAnim; target: menu; property: "appear"; to: 1; duration: 760 }
    SequentialAnimation {
        id: closeAnim
        NumberAnimation { target: menu; property: "appear"; to: 0; duration: 380; easing.type: Easing.InCubic }
        ScriptAction { script: menu.closed() }
    }
    // A button's own progress: each starts 60 ms after the one above it, and lands with a small bounce.
    function arrival(index) {
        const t = Math.max(0, Math.min(1, (appear * 760 - index * 60) / 400));
        const c1 = 1.9, c3 = c1 + 1;
        return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
    }
    // The panel unfolding from the button, again each time another is chosen.
    property real panelOpen: 0
    NumberAnimation { id: unfold; target: menu; property: "panelOpen"; from: 0; to: 1; duration: 320; easing.type: Easing.OutCubic }

    // ── The rows of each panel ───────────────────────────────────────────────
    readonly property var categories: [
        { key: "Game", label: Translation.tr("Games"), icon: "sports_esports" },
        { key: "Network", label: Translation.tr("Internet"), icon: "public" },
        { key: "Office", label: Translation.tr("Office"), icon: "description" },
        { key: "Graphics", label: Translation.tr("Graphics"), icon: "palette" },
        { key: "AudioVideo", label: Translation.tr("Sound & Video"), icon: "music_note" },
        { key: "Development", label: Translation.tr("Development"), icon: "code" },
        { key: "System", label: Translation.tr("System"), icon: "memory" },
        { key: "Utility", label: Translation.tr("Utilities"), icon: "construction" },
        { key: "", label: Translation.tr("All items"), icon: "inventory_2" }
    ]
    function appsIn(key) {
        const all = menu.host ? menu.host.apps() : [];
        return key === "" ? all : all.filter(a => (a.categories ?? []).includes(key));
    }
    readonly property int activeWorkspace: HyprlandData.monitors.find(m => m.focused)?.activeWorkspace?.id ?? 1
    readonly property var windows: HyprlandData.windowList.filter(w => (w.workspace?.id ?? 0) > 0)

    readonly property var rows: {
        switch (section) {
        case "items":
            if (query !== "")
                return LauncherSearch.results.slice(0, 40).map(r => ({
                    label: r.name, detail: r.type ?? "", icon: r.iconType === LauncherSearchResult.IconType.System ? "" : (r.iconName || "bolt"),
                    image: r.iconType === LauncherSearchResult.IconType.System ? Quickshell.iconPath(r.iconName, "application-x-executable") : "",
                    run: () => menu.host.runResult(r)
                }));
            return categories.map(c => ({ label: c.label, icon: c.icon, detail: String(menu.appsIn(c.key).length), key: c.key, opens: true }));
        case "party":
            return windows.map(w => ({
                label: w.title || w.class, detail: Translation.tr("F%1").arg(w.workspace.id),
                image: AppSearch.iconSource(AppSearch.guessIcon(w.class)),
                run: () => { Hyprland.dispatch(`hl.dsp.focus({ window = "address:${w.address}" })`); menu.host.dismiss(); }
            }));
        case "map": {
            const ids = new Set(windows.map(w => w.workspace.id));
            ids.add(activeWorkspace);
            return [...ids].sort((a, b) => a - b).map(id => ({
                label: Translation.tr("Floor %1").arg(id), icon: id === activeWorkspace ? "location_on" : "castle",
                detail: Translation.tr("%1 open").arg(windows.filter(w => w.workspace.id === id).length),
                current: id === activeWorkspace,
                run: () => { Hyprland.dispatch(`hl.dsp.focus({ workspace = ${id} })`); menu.host.dismiss(); }
            }));
        }
        case "messages": {
            const list = Notifications.list.slice().reverse().slice(0, 30).map(n => ({
                label: n.summary || n.appName, detail: n.appName, icon: "mail",
                run: () => Notifications.discardNotification(n.notificationId)
            }));
            if (list.length > 0)
                list.push({ label: Translation.tr("Clear all"), icon: "delete_sweep", run: () => Notifications.discardAllNotifications() });
            return list;
        }
        case "system":
            return [
                { label: Translation.tr("Wi-Fi"), icon: "wifi", detail: Network.wifiEnabled ? Translation.tr("ON") : Translation.tr("OFF"), run: () => Network.toggleWifi() },
                { label: Translation.tr("Bluetooth"), icon: "bluetooth", detail: BluetoothStatus.enabled ? Translation.tr("ON") : Translation.tr("OFF"),
                  run: () => { if (Bluetooth.defaultAdapter) Bluetooth.defaultAdapter.enabled = !Bluetooth.defaultAdapter.enabled; } },
                { label: Translation.tr("Do not disturb"), icon: "notifications_paused", detail: Notifications.silent ? Translation.tr("ON") : Translation.tr("OFF"),
                  run: () => Notifications.silent = !Notifications.silent },
                { label: Translation.tr("Settings"), icon: "tune", run: () => { Quickshell.execDetached(Directories.openSettingsCommand); menu.host.dismiss(); } },
                { label: Translation.tr("Lock"), icon: "lock", run: () => { menu.host.dismiss(); Session.lock(); } },
                { label: Translation.tr("Log Out"), icon: "logout", danger: true, run: () => menu.confirmLogout = true }
            ];
        default:
            return [];
        }
    }
    readonly property var subRows: section === "items" && query === "" && categoryOpen && (rows[row]?.opens ?? false)
        ? appsIn(rows[row].key).map(a => ({ label: a.name, detail: "", image: AppSearch.iconSource(a.icon ?? a.name), run: () => menu.host.launchEntry(a) }))
        : []
    property bool categoryOpen: false

    function activate(r) {
        if (!r)
            return;
        if (r.opens) {
            categoryOpen = true;
            depth = 2;
            subRow = 0;
        } else if (r.run) {
            r.run();
        }
    }

    // ── Keys ─────────────────────────────────────────────────────────────────
    focus: true
    Keys.onPressed: event => {
        const k = event.key;
        if (menu.confirmLogout) {
            if (k === Qt.Key_Escape)
                menu.confirmLogout = false;
            else if (k === Qt.Key_Return || k === Qt.Key_Enter)
                Session.logout();
            event.accepted = true;
            return;
        }
        if (k === Qt.Key_Escape) {
            if (menu.query !== "")
                menu.query = "";
            else if (menu.depth === 2) {
                menu.depth = 1;
                menu.categoryOpen = false;
            } else if (menu.depth === 1)
                menu.depth = 0;
            else
                menu.host.dismiss();
        } else if (k === Qt.Key_Up || k === Qt.Key_Down) {
            const step = k === Qt.Key_Up ? -1 : 1;
            if (menu.depth === 0)
                menu.selected = (menu.selected + step + menu.buttons.length) % menu.buttons.length;
            else if (menu.depth === 1 && menu.rows.length > 0) {
                menu.row = (menu.row + step + menu.rows.length) % menu.rows.length;
                menu.categoryOpen = false;
            } else if (menu.depth === 2 && menu.subRows.length > 0)
                menu.subRow = (menu.subRow + step + menu.subRows.length) % menu.subRows.length;
        } else if (k === Qt.Key_Right) {
            if (menu.depth === 0 && menu.rows.length > 0)
                menu.depth = 1;
            else if (menu.depth === 1 && menu.rows[menu.row]?.opens)
                menu.activate(menu.rows[menu.row]);
        } else if (k === Qt.Key_Left) {
            if (menu.depth === 2) {
                menu.depth = 1;
                menu.categoryOpen = false;
            } else if (menu.depth === 1)
                menu.depth = 0;
        } else if (k === Qt.Key_Return || k === Qt.Key_Enter) {
            if (menu.depth === 0 && menu.rows.length > 0)
                menu.depth = 1;
            else if (menu.depth === 1)
                menu.activate(menu.rows[menu.row]);
            else if (menu.depth === 2)
                menu.activate(menu.subRows[menu.subRow]);
        } else if (k === Qt.Key_Backspace) {
            menu.query = menu.query.slice(0, -1);
        } else if (event.text.length === 1 && event.text >= " ") {
            menu.query += event.text;
        } else {
            return;
        }
        event.accepted = true;
    }

    // ── Layout ───────────────────────────────────────────────────────────────
    readonly property real buttonSize: Math.round(Math.min(64, height * 0.064))
    readonly property real buttonGap: Math.round(buttonSize * 0.3)
    readonly property real columnHeight: buttons.length * buttonSize + (buttons.length - 1) * buttonGap
    readonly property real columnX: Math.round(width * 0.42)
    readonly property real columnY: Math.round((height - columnHeight) / 2)
    readonly property real rowHeight: 40
    readonly property real panelWidth: 330

    // A dim over the desktop, as the game darkens the world behind its menu.
    Rectangle {
        anchors.fill: parent
        color: "#0B1016"
        opacity: 0.38 * Math.min(1, menu.appear * 2)
    }

    // ── The player's card ────────────────────────────────────────────────────
    Item {
        id: card
        width: 360
        height: 230
        x: menu.columnX - width - 70 - (1 - Math.min(1, menu.appear * 1.4)) * 40
        y: menu.columnY + 6
        opacity: Math.min(1, menu.appear * 1.6)

        readonly property real hp: Battery.available ? Battery.percentage : 1 - ResourceUsage.memoryUsedPercentage
        readonly property real mp: 1 - ResourceUsage.memoryUsedPercentage
        readonly property real sta: 1 - ResourceUsage.cpuUsage

        // Name and level, in a plate with the corner cut, like the HUD's name tag.
        Shape {
            id: nameTag
            width: 260
            height: 38
            preferredRendererType: Shape.CurveRenderer
            ShapePath {
                strokeWidth: 1
                strokeColor: menu.plateEdge
                fillGradient: LinearGradient {
                    x1: 0; y1: 0; x2: 0; y2: 38
                    GradientStop { position: 0; color: "#FFFFFF" }
                    GradientStop { position: 1; color: "#E6EAEE" }
                }
                PathSvg { path: "M 0 0 L 246 0 L 260 14 L 260 38 L 0 38 Z" }
            }
        }
        StyledText {
            x: 14
            anchors.verticalCenter: nameTag.verticalCenter
            text: SystemInfo.username
            color: menu.ink
            font.family: menu.font
            font.pixelSize: 17
            font.weight: Font.DemiBold
            font.letterSpacing: 1
        }
        StyledText {
            x: 260 - width - 22
            anchors.verticalCenter: nameTag.verticalCenter
            text: "Lv " + Math.max(1, HyprlandData.windowList.length)
            color: menu.inkDim
            font.family: menu.font
            font.pixelSize: 13
        }

        // The HP bar: a long slanted bar that runs green, then yellow, then red as it empties.
        Item {
            id: hpBar
            y: nameTag.height + 6
            width: 340
            height: 22
            readonly property color fillColour: card.hp > 0.5 ? "#7FD15B" : card.hp > 0.2 ? "#F2C94C" : menu.crimson
            Shape {
                anchors.fill: parent
                preferredRendererType: Shape.CurveRenderer
                ShapePath {
                    strokeWidth: 1.5
                    strokeColor: menu.plateEdge
                    fillColor: "#33000000"
                    PathSvg { path: "M 0 0 L 340 0 L 326 22 L 0 22 Z" }
                }
            }
            Rectangle {
                x: 3
                y: 3
                height: 16
                width: Math.max(0, (330 - 6) * card.hp)
                color: hpBar.fillColour
                Behavior on width { NumberAnimation { duration: 400; easing.type: Easing.OutCubic } }
                Rectangle { anchors.top: parent.top; width: parent.width; height: 5; color: Qt.rgba(1, 1, 1, 0.35) }
            }
        }
        StyledText {
            anchors.right: hpBar.right
            anchors.rightMargin: 18
            anchors.top: hpBar.bottom
            anchors.topMargin: 2
            text: `${Math.round(card.hp * 100)} / 100`
            color: "#FFFFFF"
            font.family: menu.font
            font.pixelSize: 12
            style: Text.Outline
            styleColor: "#55000000"
        }

        Column {
            y: hpBar.y + hpBar.height + 26
            width: 300
            spacing: 8
            Repeater {
                model: [
                    { label: "HP", value: card.hp, note: Battery.available ? Translation.tr("battery") : Translation.tr("memory") },
                    { label: "MP", value: card.mp, note: Translation.tr("free memory") },
                    { label: "STA", value: card.sta, note: Translation.tr("idle CPU") }
                ]
                delegate: Row {
                    id: stat
                    required property var modelData
                    spacing: 10
                    StyledText {
                        width: 34
                        text: stat.modelData.label
                        color: "#FFFFFF"
                        font.family: menu.font
                        font.pixelSize: 12
                        font.weight: Font.Bold
                        style: Text.Outline
                        styleColor: "#55000000"
                    }
                    Rectangle {
                        anchors.verticalCenter: parent.verticalCenter
                        width: 180
                        height: 6
                        radius: 3
                        color: Qt.rgba(1, 1, 1, 0.22)
                        Rectangle {
                            width: parent.width * Math.max(0, Math.min(1, stat.modelData.value))
                            height: parent.height
                            radius: 3
                            color: menu.orange
                        }
                    }
                    StyledText {
                        text: stat.modelData.note
                        color: Qt.rgba(1, 1, 1, 0.75)
                        font.family: menu.font
                        font.pixelSize: 11
                    }
                }
            }
        }
        // The time, large and thin.
        StyledText {
            y: 174
            text: DateTime.time
            color: "#FFFFFF"
            font.family: menu.font
            font.pixelSize: 40
            font.weight: Font.Light
            style: Text.Outline
            styleColor: "#33000000"
        }
        StyledText {
            y: 220
            text: DateTime.date + "  ·  " + Translation.tr("Floor %1").arg(menu.activeWorkspace)
            color: Qt.rgba(1, 1, 1, 0.8)
            font.family: menu.font
            font.pixelSize: 12
            font.letterSpacing: 1
        }
    }

    // ── The column of round buttons ──────────────────────────────────────────
    Repeater {
        model: menu.buttons
        delegate: Item {
            id: button
            required property var modelData
            required property int index
            readonly property bool chosen: menu.selected === index
            readonly property real arrived: menu.arrival(index)
            width: menu.buttonSize
            height: menu.buttonSize
            x: menu.columnX
            y: menu.columnY + index * (menu.buttonSize + menu.buttonGap) - (1 - arrived) * (140 + index * 30)
            opacity: Math.max(0, Math.min(1, arrived * 1.5))

            // The glow round the chosen one, and the ring that marks keyboard focus on the column.
            Rectangle {
                anchors.centerIn: parent
                width: parent.width + 14
                height: width
                radius: width / 2
                color: "transparent"
                border.width: 3
                border.color: Qt.rgba(1, 0.75, 0.4, 0.55)
                visible: button.chosen
                scale: button.chosen ? 1 : 0.8
                Behavior on scale { NumberAnimation { duration: 180; easing.type: Easing.OutBack } }
            }
            Rectangle {
                anchors.fill: parent
                radius: width / 2
                border.width: 1
                border.color: button.chosen ? "#E08A1E" : menu.plateEdge
                gradient: Gradient {
                    GradientStop { position: 0; color: button.chosen ? menu.orangeLight : "#FFFFFF" }
                    GradientStop { position: 1; color: button.chosen ? menu.orange : "#DDE2E8" }
                }
                scale: buttonArea.pressed ? 0.92 : buttonArea.containsMouse && !button.chosen ? 1.06 : 1
                Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutBack } }
                MaterialSymbol {
                    anchors.centerIn: parent
                    text: button.modelData.icon
                    iconSize: Math.round(menu.buttonSize * 0.46)
                    fill: button.chosen ? 1 : 0
                    color: button.chosen ? "#FFFFFF" : menu.ink
                }
            }
            MouseArea {
                id: buttonArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    menu.query = "";
                    menu.selected = button.index;
                    menu.depth = 0;
                    menu.forceActiveFocus();
                }
            }
        }
    }

    // ── The panel of the chosen button ───────────────────────────────────────
    component Panel: Item {
        id: panel
        property string title
        property string icon
        property var model: []
        property int current: 0
        property bool focused: false
        property real pointerY: 0
        signal picked(int index)
        readonly property real listHeight: Math.min(model.length, 10) * menu.rowHeight
        width: menu.panelWidth
        height: 44 + Math.max(listHeight, menu.rowHeight)
        transformOrigin: Item.Left

        // The pointer at the left, at the height of what opened it.
        Shape {
            x: -11
            y: Math.max(8, Math.min(panel.height - 30, panel.pointerY - 11))
            width: 12
            height: 22
            ShapePath {
                strokeWidth: 1
                strokeColor: menu.plateEdge
                fillColor: menu.plate
                PathSvg { path: "M 12 0 L 0 11 L 12 22" }
            }
        }
        Rectangle {
            anchors.fill: parent
            radius: 4
            color: menu.plate
            border.width: 1
            border.color: menu.plateEdge
        }
        // The heading: the section's icon and name, a fine rule under it.
        Row {
            x: 14
            y: 12
            spacing: 8
            MaterialSymbol {
                text: panel.icon
                iconSize: 18
                color: menu.orange
            }
            StyledText {
                anchors.verticalCenter: parent.verticalCenter
                text: panel.title.toUpperCase()
                color: menu.inkDim
                font.family: menu.font
                font.pixelSize: 13
                font.weight: Font.DemiBold
                font.letterSpacing: 2
            }
        }
        Rectangle {
            x: 10
            y: 40
            width: parent.width - 20
            height: 1
            color: menu.rowLine
        }
        StyledText {
            visible: panel.model.length === 0
            x: 18
            y: 44 + (menu.rowHeight - height) / 2
            text: Translation.tr("Nothing here")
            color: menu.inkDim
            font.family: menu.font
            font.pixelSize: 13
            font.italic: true
        }
        ListView {
            id: list
            x: 4
            y: 44
            width: parent.width - 8
            height: panel.listHeight
            clip: true
            model: panel.model
            currentIndex: panel.current
            interactive: count > 10
            highlightMoveDuration: 120
            onCurrentIndexChanged: positionViewAtIndex(currentIndex, ListView.Contain)
            delegate: Item {
                id: rowItem
                required property var modelData
                required property int index
                readonly property bool lit: (panel.focused && panel.current === index) || rowArea.containsMouse
                width: list.width
                height: menu.rowHeight
                // Each row slides in a moment after the one above it.
                opacity: Math.max(0, Math.min(1, menu.panelOpen * 3 - index * 0.25))
                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 2
                    radius: 3
                    color: rowItem.lit ? (rowItem.modelData.danger ? menu.crimson : menu.orange) : "transparent"
                    Behavior on color { ColorAnimation { duration: 100 } }
                }
                Rectangle {
                    visible: !rowItem.lit && rowItem.index > 0
                    x: 10
                    width: parent.width - 20
                    height: 1
                    color: menu.rowLine
                }
                // The icon: the app's, or a symbol in a small round plate.
                Item {
                    id: rowIcon
                    x: 10
                    anchors.verticalCenter: parent.verticalCenter
                    width: 26
                    height: 26
                    IconImage {
                        anchors.fill: parent
                        visible: (rowItem.modelData.image ?? "") !== ""
                        source: rowItem.modelData.image ?? ""
                    }
                    Rectangle {
                        anchors.fill: parent
                        visible: (rowItem.modelData.image ?? "") === ""
                        radius: width / 2
                        color: rowItem.lit ? Qt.rgba(1, 1, 1, 0.25) : (rowItem.modelData.current ? menu.orange : "#E3E8ED")
                        MaterialSymbol {
                            anchors.centerIn: parent
                            text: rowItem.modelData.icon ?? "circle"
                            iconSize: 16
                            color: rowItem.lit || rowItem.modelData.current ? "#FFFFFF" : menu.ink
                        }
                    }
                }
                StyledText {
                    anchors.left: rowIcon.right
                    anchors.leftMargin: 12
                    anchors.right: detail.left
                    anchors.rightMargin: 8
                    anchors.verticalCenter: parent.verticalCenter
                    text: rowItem.modelData.label ?? ""
                    elide: Text.ElideRight
                    color: rowItem.lit ? "#FFFFFF" : (rowItem.modelData.danger ? menu.crimson : menu.ink)
                    font.family: menu.font
                    font.pixelSize: 14
                }
                StyledText {
                    id: detail
                    anchors.right: chevron.left
                    anchors.rightMargin: 4
                    anchors.verticalCenter: parent.verticalCenter
                    text: rowItem.modelData.detail ?? ""
                    color: rowItem.lit ? "#FFFFFF" : menu.inkDim
                    font.family: menu.font
                    font.pixelSize: 12
                }
                MaterialSymbol {
                    id: chevron
                    anchors.right: parent.right
                    anchors.rightMargin: 8
                    anchors.verticalCenter: parent.verticalCenter
                    visible: rowItem.modelData.opens ?? false
                    text: "chevron_right"
                    iconSize: 18
                    color: rowItem.lit ? "#FFFFFF" : menu.inkDim
                }
                MouseArea {
                    id: rowArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: panel.picked(rowItem.index)
                }
            }
        }
    }

    // The Status panel is a sheet of figures rather than a list.
    readonly property var statusRows: [
        { label: Translation.tr("Name"), detail: SystemInfo.username, icon: "badge" },
        { label: Translation.tr("Level"), detail: String(Math.max(1, HyprlandData.windowList.length)), icon: "military_tech" },
        { label: Translation.tr("HP"), detail: `${Math.round(card.hp * 100)}%`, icon: "favorite" },
        { label: Translation.tr("MP"), detail: `${Math.round(card.mp * 100)}%`, icon: "water_drop" },
        { label: Translation.tr("Floor"), detail: String(activeWorkspace), icon: "castle" },
        { label: Translation.tr("Time played"), detail: DateTime.uptime, icon: "schedule" },
        { label: Translation.tr("World"), detail: SystemInfo.distroName ?? "Linux", icon: "public" }
    ]

    Panel {
        id: mainPanel
        x: menu.columnX + menu.buttonSize + 30
        y: Math.max(20, Math.min(menu.height - height - 20, menu.columnY + menu.selected * (menu.buttonSize + menu.buttonGap) + menu.buttonSize / 2 - 22 - menu.rowHeight / 2))
        pointerY: menu.columnY + menu.selected * (menu.buttonSize + menu.buttonGap) + menu.buttonSize / 2 - y
        title: menu.query !== "" ? `${menu.buttons[1].label} · ${menu.query}` : (menu.buttons[menu.selected]?.label ?? "")
        icon: menu.query !== "" ? "search" : (menu.buttons[menu.selected]?.icon ?? "")
        model: menu.section === "status" ? menu.statusRows : menu.rows
        current: menu.row
        focused: menu.depth >= 1
        opacity: Math.min(1, menu.panelOpen * 1.5) * Math.min(1, Math.max(0, menu.appear * 2 - 0.6))
        scale: 0.85 + 0.15 * menu.panelOpen
        onPicked: index => {
            menu.row = index;
            menu.depth = 1;
            menu.categoryOpen = false;
            if (menu.section !== "status")
                menu.activate(menu.rows[index]);
            menu.forceActiveFocus();
        }
    }

    // Items: the apps of the category chosen.
    Panel {
        id: subPanel
        visible: menu.subRows.length > 0
        x: mainPanel.x + mainPanel.width + 26
        y: Math.max(20, Math.min(menu.height - height - 20, mainPanel.y + 44 + menu.row * menu.rowHeight - 22))
        pointerY: mainPanel.y + 44 + menu.row * menu.rowHeight + menu.rowHeight / 2 - y
        title: menu.rows[menu.row]?.label ?? ""
        icon: menu.rows[menu.row]?.icon ?? ""
        model: menu.subRows
        current: menu.subRow
        focused: menu.depth === 2
        opacity: visible ? 1 : 0
        onPicked: index => menu.activate(menu.subRows[index])
    }

    // ── Log Out: the game's dialog ───────────────────────────────────────────
    Rectangle {
        anchors.fill: parent
        visible: menu.confirmLogout
        color: Qt.rgba(0.04, 0.06, 0.09, 0.45)
        MouseArea {
            anchors.fill: parent
            onClicked: menu.confirmLogout = false
        }
        Rectangle {
            id: dialog
            anchors.centerIn: parent
            width: 420
            height: 200
            radius: 4
            color: menu.plate
            border.width: 1
            border.color: menu.plateEdge
            scale: menu.confirmLogout ? 1 : 0.8
            Behavior on scale { NumberAnimation { duration: 220; easing.type: Easing.OutBack } }
            MouseArea { anchors.fill: parent }
            StyledText {
                anchors.horizontalCenter: parent.horizontalCenter
                y: 16
                text: Translation.tr("Log Out")
                color: menu.inkDim
                font.family: menu.font
                font.pixelSize: 14
                font.weight: Font.DemiBold
                font.letterSpacing: 2
            }
            Rectangle { x: 14; y: 44; width: parent.width - 28; height: 1; color: menu.rowLine }
            StyledText {
                anchors.horizontalCenter: parent.horizontalCenter
                y: 66
                text: Translation.tr("Are you sure you want to log out?")
                color: menu.ink
                font.family: menu.font
                font.pixelSize: 16
            }
            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                y: 112
                spacing: 64
                Repeater {
                    model: [
                        { glyph: "○", colour: menu.okBlue, act: () => Session.logout() },
                        { glyph: "✕", colour: menu.crimson, act: () => menu.confirmLogout = false }
                    ]
                    delegate: Rectangle {
                        id: choice
                        required property var modelData
                        width: 58
                        height: 58
                        radius: 29
                        color: choice.modelData.colour
                        border.width: 3
                        border.color: Qt.lighter(choice.modelData.colour, 1.35)
                        scale: choiceArea.pressed ? 0.9 : choiceArea.containsMouse ? 1.08 : 1
                        Behavior on scale { NumberAnimation { duration: 130; easing.type: Easing.OutBack } }
                        StyledText {
                            anchors.centerIn: parent
                            text: choice.modelData.glyph
                            color: "#FFFFFF"
                            font.pixelSize: 26
                            font.weight: Font.Bold
                        }
                        MouseArea {
                            id: choiceArea
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: choice.modelData.act()
                        }
                    }
                }
            }
        }
    }
}
