pragma ComponentBehavior: Bound
import qs
import qs.services
import qs.modules.common
import qs.modules.common.functions
import qs.modules.common.widgets
import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Hyprland

/**
 * Halcyon's mini window manager (Super+Shift+W).
 *
 * Every open window as a live thumbnail, most recently used first, with
 * minimised windows on a shelf below. Type to filter; arrows move; Enter
 * focuses (or restores); Ctrl + M minimises, H hides the app, F floats,
 * P pins, C centres, Q (or Delete) closes; Esc leaves. Hover a window for
 * the same as buttons.
 *
 * The heavy lifting is halcyon-windows (minimise stack, Lua dispatchers);
 * this is a view on HyprlandData, which updates on every Hyprland event.
 */
Scope {
    id: root

    readonly property string tool: `${FileUtils.trimFileProtocol(Directories.config)}/hypr/hyprland/halcyon/halcyon-windows`
    readonly property string minimisedName: "special:minimised"

    function run(args) {
        Quickshell.execDetached([root.tool, ...args]);
    }

    Loader {
        id: loader
        active: GlobalStates.windowManagerOpen

        sourceComponent: PanelWindow {
            id: panel
            visible: true
            color: "transparent"
            exclusiveZone: 0
            WlrLayershell.namespace: "quickshell:windowManager"
            WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive
            anchors {
                top: true
                bottom: true
                left: true
                right: true
            }
            mask: Region {
                item: card
            }

            function close() {
                GlobalStates.windowManagerOpen = false;
            }

            Component.onCompleted: GlobalFocusGrab.addDismissable(panel)
            Component.onDestruction: GlobalFocusGrab.removeDismissable(panel)
            Connections {
                target: GlobalFocusGrab
                function onDismissed() {
                    panel.close();
                }
            }

            // ---- data ---------------------------------------------------

            property string filter: ""
            property int selected: 0

            function matches(w) {
                const q = panel.filter.trim().toLowerCase();
                return q.length === 0 || (w.title ?? "").toLowerCase().includes(q) || (w.class ?? "").toLowerCase().includes(q);
            }
            // Real windows only (mapped, titled), most recently used first.
            readonly property var allWindows: HyprlandData.windowList.filter(w => w.mapped !== false && (w.title ?? "").length > 0)
            readonly property var openWindows: allWindows.filter(w => w.workspace?.name !== root.minimisedName && matches(w)).sort((a, b) => (a.focusHistoryID ?? 999) - (b.focusHistoryID ?? 999))
            readonly property var minimisedWindows: allWindows.filter(w => w.workspace?.name === root.minimisedName && matches(w))
            // One list for keyboard navigation: open windows, then the shelf.
            readonly property var ordered: openWindows.concat(minimisedWindows)
            readonly property var current: ordered.length > 0 ? ordered[Math.min(selected, ordered.length - 1)] : null

            onFilterChanged: selected = 0

            function toplevelFor(address) {
                return ToplevelManager.toplevels.values.find(t => `0x${t.HyprlandToplevel?.address}` === address) ?? null;
            }

            function act(verb, w) {
                if (!w)
                    return;
                const minimised = w.workspace?.name === root.minimisedName;
                if (verb === "focus") {
                    root.run([minimised ? "restore" : "focus", w.address]);
                    panel.close();
                } else if (verb === "minimise") {
                    root.run([minimised ? "restore" : "minimise", w.address]);
                } else {
                    root.run([verb, w.address]);
                }
            }

            // ---- the card -----------------------------------------------

            StyledRectangularShadow {
                target: card
            }

            Rectangle {
                id: card
                anchors.centerIn: parent
                width: Math.min(panel.width * 0.78, 1180)
                height: Math.min(panel.height * 0.78, content.implicitHeight + 40)
                radius: Appearance.rounding.windowRounding
                color: Appearance.colors.colLayer0
                border.width: 1
                border.color: Appearance.colors.colLayer0Border
                clip: true

                scale: 0.94
                opacity: 0
                Component.onCompleted: {
                    scale = 1;
                    opacity = 1;
                }
                Behavior on scale {
                    animation: Appearance.animation.elementMoveEnter.numberAnimation.createObject(this)
                }
                Behavior on opacity {
                    animation: Appearance.animation.elementMoveFast.numberAnimation.createObject(this)
                }

                Keys.onPressed: event => {
                    const columns = Math.max(1, grid.columns);
                    const count = panel.ordered.length;
                    if (event.key === Qt.Key_Escape) {
                        panel.close();
                    } else if (event.key === Qt.Key_Right || (event.key === Qt.Key_Tab && !(event.modifiers & Qt.ShiftModifier))) {
                        panel.selected = (panel.selected + 1) % Math.max(count, 1);
                    } else if (event.key === Qt.Key_Left || event.key === Qt.Key_Backtab) {
                        panel.selected = (panel.selected - 1 + count) % Math.max(count, 1);
                    } else if (event.key === Qt.Key_Down) {
                        panel.selected = Math.min(panel.selected + columns, count - 1);
                    } else if (event.key === Qt.Key_Up) {
                        panel.selected = Math.max(panel.selected - columns, 0);
                    } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                        panel.act("focus", panel.current);
                    } else if (event.key === Qt.Key_Delete && search.text.length === 0) {
                        panel.act("close", panel.current);
                    } else if (event.modifiers === Qt.ControlModifier) {
                        // Ctrl + letter acts on the selection; plain letters filter.
                        const verbs = {
                            [Qt.Key_M]: "minimise",
                            [Qt.Key_F]: "float",
                            [Qt.Key_P]: "pin",
                            [Qt.Key_C]: "centre",
                            [Qt.Key_Q]: "close"
                        };
                        if (event.key === Qt.Key_H) {
                            if (panel.current)
                                root.run(["hide", panel.current.address]);
                        } else if (verbs[event.key] !== undefined) {
                            panel.act(verbs[event.key], panel.current);
                        } else {
                            return;
                        }
                    } else {
                        return;
                    }
                    event.accepted = true;
                }

                ColumnLayout {
                    id: content
                    anchors {
                        fill: parent
                        margins: 20
                    }
                    spacing: 14

                    // Header: title, search, restore-all
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        MaterialSymbol {
                            text: "select_window"
                            iconSize: Appearance.font.pixelSize.hugeass
                            color: Appearance.colors.colPrimary
                        }
                        StyledText {
                            text: Translation.tr("Windows")
                            font.pixelSize: Appearance.font.pixelSize.larger
                        }
                        StyledText {
                            text: Translation.tr("%1 open").arg(panel.openWindows.length) + (panel.minimisedWindows.length > 0 ? Translation.tr(" · %1 minimised").arg(panel.minimisedWindows.length) : "")
                            color: Appearance.colors.colSubtext
                            font.pixelSize: Appearance.font.pixelSize.small
                        }
                        Item {
                            Layout.fillWidth: true
                        }
                        ToolbarTextField {
                            id: search
                            implicitWidth: 260
                            implicitHeight: 40
                            placeholderText: Translation.tr("Filter windows")
                            focus: true
                            Component.onCompleted: forceActiveFocus()
                            onTextChanged: panel.filter = text
                            Keys.forwardTo: [card]
                        }
                    }

                    // Open windows
                    Flickable {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredHeight: grid.implicitHeight
                        contentHeight: grid.implicitHeight
                        clip: true
                        boundsBehavior: Flickable.StopAtBounds

                        GridLayout {
                            id: grid
                            width: parent.width
                            columns: Math.max(1, Math.floor(width / 270))
                            columnSpacing: 12
                            rowSpacing: 12

                            Repeater {
                                model: ScriptModel {
                                    values: panel.openWindows
                                    objectProp: "address"
                                }
                                delegate: WindowTile {
                                    required property var modelData
                                    required property int index
                                    Layout.fillWidth: true
                                    windowData: modelData
                                    toplevel: panel.toplevelFor(modelData.address)
                                    selected: panel.selected === index
                                    live: loader.active
                                    onActivated: verb => panel.act(verb, modelData)
                                    onHoveredChanged: if (hovered) panel.selected = index
                                }
                            }
                        }

                        StyledText {
                            anchors.centerIn: parent
                            visible: panel.openWindows.length === 0
                            text: panel.filter.length > 0 ? Translation.tr("No window matches “%1”").arg(panel.filter) : Translation.tr("No open windows")
                            color: Appearance.colors.colSubtext
                        }
                    }

                    // The minimised shelf
                    ColumnLayout {
                        Layout.fillWidth: true
                        visible: panel.minimisedWindows.length > 0
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true
                            StyledText {
                                text: Translation.tr("Minimised")
                                color: Appearance.colors.colSubtext
                                font.pixelSize: Appearance.font.pixelSize.small
                            }
                            Item {
                                Layout.fillWidth: true
                            }
                            RippleButtonWithIcon {
                                buttonRadius: Appearance.rounding.full
                                materialIcon: "restore_page"
                                mainText: Translation.tr("Restore all")
                                onClicked: root.run(["restore", "--all"])
                            }
                        }

                        Flow {
                            Layout.fillWidth: true
                            spacing: 8
                            Repeater {
                                model: ScriptModel {
                                    values: panel.minimisedWindows
                                    objectProp: "address"
                                }
                                delegate: RippleButton {
                                    id: chip
                                    required property var modelData
                                    required property int index
                                    readonly property bool isSelected: panel.selected === panel.openWindows.length + index
                                    implicitHeight: 40
                                    implicitWidth: chipRow.implicitWidth + 24
                                    buttonRadius: Appearance.rounding.full
                                    toggled: isSelected
                                    onClicked: panel.act("focus", modelData)
                                    altAction: () => panel.act("close", modelData)
                                    contentItem: RowLayout {
                                        id: chipRow
                                        anchors.centerIn: parent
                                        spacing: 8
                                        StyledImage {
                                            source: Quickshell.iconPath(AppSearch.guessIcon(chip.modelData.class), "image-missing")
                                            sourceSize: Qt.size(22, 22)
                                            Layout.preferredWidth: 22
                                            Layout.preferredHeight: 22
                                        }
                                        StyledText {
                                            text: chip.modelData.title
                                            elide: Text.ElideRight
                                            Layout.maximumWidth: 220
                                            color: chip.isSelected ? Appearance.colors.colOnPrimary : Appearance.colors.colOnLayer1
                                        }
                                    }
                                    StyledToolTip {
                                        text: Translation.tr("Click to restore · right-click to close")
                                    }
                                }
                            }
                        }
                    }

                    StyledText {
                        Layout.alignment: Qt.AlignHCenter
                        text: Translation.tr("Type to filter · Enter focus · Ctrl + M minimise · H hide app · F float · P pin · C centre · Q close · Esc leave")
                        color: Appearance.colors.colSubtext
                        font.pixelSize: Appearance.font.pixelSize.smaller
                    }
                }
            }
        }
    }

    IpcHandler {
        target: "windowManager"
        function toggle(): void {
            GlobalStates.windowManagerOpen = !GlobalStates.windowManagerOpen;
        }
        function open(): void {
            GlobalStates.windowManagerOpen = true;
        }
        function close(): void {
            GlobalStates.windowManagerOpen = false;
        }
    }

    GlobalShortcut {
        name: "windowManagerToggle"
        description: "Toggles the Halcyon window manager"
        onPressed: GlobalStates.windowManagerOpen = !GlobalStates.windowManagerOpen
    }
}
