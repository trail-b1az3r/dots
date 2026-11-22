pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Effects
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Hyprland
import qs.common
import qs.services

// The theme picker (Super+Shift+T, Ctrl+Super+Shift+T, right-click the mountain): every Halcyon theme as a card
// with its wallpaper and colours on frosted glass, six to a page. Arrows choose (and cross pages), PgUp/PgDn, [ ],
// the wheel or the dots turn pages, typing searches, Enter or a click applies, Esc closes.
Scope {
    id: root

    property bool open: false
    property var themes: []
    property string query: ""
    property int sel: 0
    readonly property string tool: Quickshell.env("HOME") + "/.config/hypr/hyprland/halcyon/halcyon-theme"
    readonly property var shown: {
        const q = root.query.trim().toLowerCase();
        if (q === "")
            return root.themes;
        return root.themes.filter(t => t.name.toLowerCase().includes(q) || t.description.toLowerCase().includes(q));
    }

    function toggle() {
        root.open = !root.open;
        if (root.open) {
            root.query = "";
            list.running = true;
        }
    }
    function apply(id) {
        root.open = false;
        Quickshell.execDetached([root.tool, "apply", id]);
    }
    // A theme's picture: its preview, else its wallpaper when that is a picture (an animated one shows its colours).
    function picture(t) {
        if (t.preview)
            return "file://" + t.preview;
        if (t.has_wallpaper && /\.(jpe?g|png|webp|bmp)$/i.test(t.wallpaper))
            return "file://" + t.wallpaper;
        return "";
    }

    Connections {
        target: Actions
        function onThemesRequested() { root.toggle(); }
    }

    Process {
        id: list
        command: [root.tool, "list", "--json"]
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    root.themes = JSON.parse(text).themes ?? [];
                    root.sel = Math.max(0, root.themes.findIndex(t => t.active));
                } catch (e) {
                    root.themes = [];
                }
            }
        }
    }

    Loader {
        active: root.open
        sourceComponent: PanelWindow {
            id: win
            screen: Quickshell.screens.find(s => s.name === Hyprland.focusedMonitor?.name) ?? Quickshell.screens[0]
            WlrLayershell.namespace: "summit-themes"
            WlrLayershell.layer: WlrLayer.Overlay
            WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive
            exclusionMode: ExclusionMode.Ignore
            color: "transparent"
            anchors { top: true; bottom: true; left: true; right: true }

            // A click outside closes.
            MouseArea {
                anchors.fill: parent
                onClicked: root.open = false
            }

            Glass {
                id: panel
                width: Math.min(900, win.width - 120)
                height: Math.min(580, win.height - 160)
                anchors.centerIn: parent
                radius: 26
                tint: Theme.glassTint + 0.12
                opacity: 0
                scale: 0.97
                Component.onCompleted: { opacity = 1; scale = 1; keys.forceActiveFocus(); }
                Behavior on opacity { NumberAnimation { duration: 140 } }
                Behavior on scale { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }

                readonly property int cols: width >= 700 ? 3 : 2
                readonly property int perPage: cols * 2
                readonly property int pages: Math.max(1, Math.ceil(root.shown.length / perPage))
                readonly property int page: Math.min(pages - 1, Math.floor(root.sel / perPage))
                // A new page slides in from the side it comes from.
                property int shownPage: 0
                onPageChanged: {
                    slide.from = page > shownPage ? 60 : -60;
                    shownPage = page;
                    pageIn.restart();
                }
                readonly property var selected: root.shown[Math.min(root.sel, root.shown.length - 1)] ?? null
                function move(by) {
                    if (root.shown.length > 0)
                        root.sel = Math.max(0, Math.min(root.shown.length - 1, root.sel + by));
                }
                function turn(p) {
                    p = Math.max(0, Math.min(pages - 1, p));
                    if (root.shown.length > 0)
                        root.sel = Math.min(root.shown.length - 1, p * perPage + root.sel % perPage);
                }

                MouseArea {
                    anchors.fill: parent    // clicks between the cards stay here
                    onWheel: wheel => {
                        const d = wheel.angleDelta.y !== 0 ? wheel.angleDelta.y : -wheel.angleDelta.x;
                        if (Math.abs(d) >= 60)
                            panel.turn(panel.page + (d < 0 ? 1 : -1));
                    }
                }

                Item {
                    id: keys
                    focus: true
                    Keys.onPressed: event => {
                        const k = event.key;
                        if (k === Qt.Key_Escape) {
                            if (root.query !== "") root.query = ""; else root.open = false;
                        } else if (k === Qt.Key_Left) panel.move(-1);
                        else if (k === Qt.Key_Right) panel.move(1);
                        else if (k === Qt.Key_Up) panel.move(-panel.cols);
                        else if (k === Qt.Key_Down) panel.move(panel.cols);
                        else if (k === Qt.Key_PageUp || k === Qt.Key_BracketLeft) panel.turn(panel.page - 1);
                        else if (k === Qt.Key_PageDown || k === Qt.Key_BracketRight) panel.turn(panel.page + 1);
                        else if ((k === Qt.Key_Return || k === Qt.Key_Enter) && panel.selected) root.apply(panel.selected.id);
                        else if (k === Qt.Key_Backspace) { root.query = root.query.slice(0, -1); root.sel = 0; }
                        else if (event.text.length === 1 && event.text > " " && !(event.modifiers & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier))) {
                            root.query += event.text;
                            root.sel = 0;
                        } else return;
                        event.accepted = true;
                    }
                }

                // Header: the title, and the search as you type.
                Text {
                    x: 26; y: 22
                    text: "Themes"
                    color: Theme.text
                    font.family: Theme.font
                    font.pixelSize: 17
                    font.weight: Font.DemiBold
                }
                Glass {
                    anchors { right: parent.right; rightMargin: 24; top: parent.top; topMargin: 18 }
                    width: 230; height: 32; radius: 16
                    tint: 0.25
                    highlight: 0.04
                    Symbol { x: 10; anchors.verticalCenter: parent.verticalCenter; name: "search"; size: 17; color: Theme.muted }
                    Text {
                        x: 34; anchors.verticalCenter: parent.verticalCenter
                        width: parent.width - 44
                        elide: Text.ElideLeft
                        text: root.query !== "" ? root.query : "Type to search"
                        color: root.query !== "" ? Theme.text : Theme.muted
                        font.family: Theme.font
                        font.pixelSize: 13
                    }
                }

                // The page of cards.
                ParallelAnimation {
                    id: pageIn
                    NumberAnimation { id: slide; target: gridShift; property: "x"; to: 0; duration: Theme.enterMs; easing.type: Easing.OutCubic }
                    NumberAnimation { target: grid; property: "opacity"; from: 0.2; to: 1; duration: Theme.animMs + 80; easing.type: Easing.OutCubic }
                }

                Item {
                    id: grid
                    transform: Translate { id: gridShift }
                    x: 18; y: 66
                    width: parent.width - 36
                    height: parent.height - 66 - 78
                    readonly property real cellW: width / panel.cols
                    readonly property real cellH: height / 2

                    Repeater {
                        model: root.shown.slice(panel.page * panel.perPage, (panel.page + 1) * panel.perPage)
                        delegate: Item {
                            id: card
                            required property int index
                            required property var modelData
                            readonly property int at: panel.page * panel.perPage + index
                            readonly property bool sel: root.sel === at
                            x: (index % panel.cols) * grid.cellW
                            y: Math.floor(index / panel.cols) * grid.cellH
                            width: grid.cellW
                            height: grid.cellH
                            // The selected card lifts toward you; a press pushes it back.
                            scale: cardArea.pressed ? 0.97 : card.sel ? 1.035 : 1
                            Behavior on scale { SpringAnimation { spring: Theme.springStiffness * 1.3; damping: Theme.springDamping; epsilon: 0.001 } }

                            Item {
                                id: pic
                                x: 6; y: 6
                                width: parent.width - 12
                                height: parent.height - 44
                                Rectangle {
                                    id: mask
                                    anchors.fill: parent
                                    radius: 14
                                    visible: false
                                    layer.enabled: true
                                }
                                Item {
                                    anchors.fill: parent
                                    layer.enabled: true
                                    layer.effect: MultiEffect {
                                        maskEnabled: true
                                        maskSource: mask
                                        maskThresholdMin: 0.5
                                        maskSpreadAtMin: 1.0
                                    }
                                    Rectangle {
                                        anchors.fill: parent
                                        gradient: Gradient {
                                            GradientStop { position: 0; color: card.modelData.colors.surface_container }
                                            GradientStop { position: 1; color: card.modelData.colors.background }
                                        }
                                    }
                                    Image {
                                        anchors.fill: parent
                                        source: root.picture(card.modelData)
                                        sourceSize.width: 480
                                        fillMode: Image.PreserveAspectCrop
                                        asynchronous: true
                                    }
                                    Row {
                                        anchors { left: parent.left; bottom: parent.bottom; margins: 10 }
                                        spacing: 4
                                        Repeater {
                                            model: ["primary", "secondary", "tertiary"]
                                            Rectangle {
                                                required property string modelData
                                                width: 12; height: 12; radius: 6
                                                color: card.modelData.colors[modelData]
                                                border.width: 1
                                                border.color: Qt.rgba(1, 1, 1, 0.55)
                                            }
                                        }
                                    }
                                }
                                Rectangle {
                                    anchors.fill: parent
                                    radius: 14
                                    color: "transparent"
                                    border.width: card.sel ? 3 : (card.modelData.active ? 2 : 0)
                                    border.color: card.sel ? Theme.accent : Theme.alpha("#FFFFFF", 0.8)
                                }
                            }
                            Row {
                                x: 10
                                anchors.top: pic.bottom; anchors.topMargin: 9
                                width: parent.width - 20
                                spacing: 8
                                Text {
                                    width: Math.min(implicitWidth, parent.width - (current.visible ? current.width + 8 : 0))
                                    elide: Text.ElideRight
                                    text: card.modelData.name
                                    color: Theme.text
                                    font.family: Theme.font
                                    font.pixelSize: 13
                                    font.weight: Font.Medium
                                }
                                Rectangle {
                                    id: current
                                    visible: card.modelData.active === true
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: currentText.implicitWidth + 14; height: 18; radius: 9
                                    color: Theme.alpha(Theme.accent, 0.22)
                                    Text {
                                        id: currentText
                                        anchors.centerIn: parent
                                        text: "Current"
                                        color: Theme.accent
                                        font.family: Theme.font
                                        font.pixelSize: 10
                                        font.weight: Font.DemiBold
                                    }
                                }
                            }
                            MouseArea {
                                id: cardArea
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onPositionChanged: root.sel = card.at
                                onClicked: root.apply(card.modelData.id)
                            }
                        }
                    }
                    Text {
                        visible: root.shown.length === 0
                        anchors.centerIn: parent
                        text: root.query !== "" ? `No themes match “${root.query}”` : "Loading…"
                        color: Theme.muted
                        font.family: Theme.font
                        font.pixelSize: 13
                    }
                }

                // Footer: what the selected theme is, and the pages.
                Text {
                    x: 26
                    anchors { bottom: parent.bottom; bottomMargin: 46 }
                    width: parent.width - 52
                    elide: Text.ElideRight
                    text: panel.selected?.description ?? ""
                    color: Theme.muted
                    font.family: Theme.font
                    font.pixelSize: 12
                }
                Row {
                    anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.bottom; bottomMargin: 18 }
                    spacing: 8
                    visible: panel.pages > 1
                    Repeater {
                        model: panel.pages
                        Rectangle {
                            required property int index
                            width: index === panel.page ? 22 : 7
                            height: 7
                            radius: 3.5
                            color: index === panel.page ? Theme.accent : Theme.alpha(Theme.text, 0.25)
                            Behavior on width { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
                            MouseArea { anchors.fill: parent; anchors.margins: -6; onClicked: panel.turn(parent.index) }
                        }
                    }
                }
                Text {
                    anchors { right: parent.right; rightMargin: 26; bottom: parent.bottom; bottomMargin: 14 }
                    text: "Enter applies  ·  PgUp PgDn pages"
                    color: Theme.alpha(Theme.muted, 0.8)
                    font.family: Theme.font
                    font.pixelSize: 11
                }
            }
        }
    }
}
