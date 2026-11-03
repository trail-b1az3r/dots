pragma ComponentBehavior: Bound

import qs
import qs.services
import qs.modules.common
import qs.modules.common.widgets
import QtQuick
import Quickshell
import Quickshell.Hyprland
import Quickshell.Widgets

/**
 * Every workspace and the apps open on it, for the themed app pickers: the manga book's tablet and the ICEY phone's
 * folded-out screen. Click an app to go to it. Hold Shift and drag an app onto another workspace to move it there;
 * the last tile is an empty workspace, for moving an app somewhere new.
 *
 * The look comes from outside (ink, paper, accent, corner), so each picker draws it in its own style.
 */
Item {
    id: board

    property color ink: Appearance.colors.colOnLayer1
    property color paper: Appearance.colors.colLayer1
    property color accent: Appearance.colors.colPrimary
    property real corner: 6
    property real border: 2
    property int columns: 4
    // After an app was clicked and focused: the picker closes.
    signal picked

    readonly property var windows: HyprlandData.windowList.filter(w => (w.workspace?.id ?? 0) > 0)
    readonly property int activeId: HyprlandData.monitors.find(m => m.focused)?.activeWorkspace?.id ?? 1
    // The workspaces with apps on them, the ones shown on a monitor, and one empty one after them.
    readonly property var workspaceIds: {
        const ids = new Set(board.windows.map(w => w.workspace.id));
        for (const m of HyprlandData.monitors)
            if ((m.activeWorkspace?.id ?? 0) > 0)
                ids.add(m.activeWorkspace.id);
        const sorted = [...ids].sort((a, b) => a - b);
        sorted.push((sorted.length ? sorted[sorted.length - 1] : 0) + 1);
        return sorted;
    }

    // The app being moved with Shift + drag, where it is, and the workspace under it.
    property var dragging: null
    property point dragAt: Qt.point(0, 0)
    property int dropTarget: -1

    function iconFor(w) {
        return AppSearch.iconSource(AppSearch.guessIcon(w?.class ?? ""));
    }
    function tileAt(point) {
        for (let i = 0; i < tiles.count; i++) {
            const tile = tiles.itemAt(i);
            const p = tile.mapFromItem(board, point.x, point.y);
            if (p.x >= 0 && p.y >= 0 && p.x < tile.width && p.y < tile.height)
                return board.workspaceIds[i];
        }
        return -1;
    }
    function dragTo(point) {
        dragAt = point;
        dropTarget = tileAt(point);
    }
    function drop() {
        const w = dragging;
        dragging = null;
        if (!w || dropTarget < 0 || dropTarget === w.workspace?.id)
            return;
        Hyprland.dispatch(`hl.dsp.window.move({ workspace = "${dropTarget}", follow = false, window = "address:${w.address}" })`);
        dropTarget = -1;
    }

    Grid {
        id: grid
        anchors.fill: parent
        // As few rows as `columns` allows, then the columns spread evenly over them (6 tiles: 3 and 3, not 4 and 2).
        readonly property int rows: Math.max(1, Math.ceil(board.workspaceIds.length / board.columns))
        columns: Math.max(1, Math.ceil(board.workspaceIds.length / rows))
        spacing: 12
        readonly property real tileW: (width - spacing * (columns - 1)) / columns
        readonly property real tileH: (height - spacing * (rows - 1)) / rows

        Repeater {
            id: tiles
            model: board.workspaceIds
            delegate: Rectangle {
                id: tile
                required property int modelData
                readonly property var apps: board.windows.filter(w => w.workspace.id === tile.modelData)
                readonly property bool target: board.dragging !== null && board.dropTarget === tile.modelData
                width: grid.tileW
                height: Math.min(grid.tileH, grid.tileW)
                radius: board.corner
                color: tile.target ? Qt.rgba(board.accent.r, board.accent.g, board.accent.b, 0.22) : board.paper
                border.width: tile.modelData === board.activeId || tile.target ? board.border + 1 : board.border
                border.color: tile.target || tile.modelData === board.activeId ? board.accent : board.ink
                Behavior on color { ColorAnimation { duration: 120 } }

                StyledText {
                    id: tileTitle
                    x: 10
                    y: 6
                    text: tile.apps.length === 0 && tile.modelData === board.workspaceIds[board.workspaceIds.length - 1]
                        ? Translation.tr("%1 · new").arg(tile.modelData) : Translation.tr("Workspace %1").arg(tile.modelData)
                    color: tile.modelData === board.activeId ? board.accent : board.ink
                    font.pixelSize: 15
                    font.weight: Font.Black
                }
                Flow {
                    anchors {
                        top: tileTitle.bottom
                        left: parent.left
                        right: parent.right
                        bottom: parent.bottom
                        margins: 8
                        topMargin: 4
                    }
                    spacing: 6
                    Repeater {
                        model: tile.apps
                        delegate: Item {
                            id: app
                            required property var modelData
                            readonly property real size: Math.max(26, Math.min(44, tile.height * 0.34))
                            width: size
                            height: size
                            opacity: board.dragging?.address === app.modelData.address ? 0.3 : 1
                            IconImage {
                                anchors.fill: parent
                                source: board.iconFor(app.modelData)
                                scale: appArea.containsMouse ? 1.12 : 1
                                Behavior on scale { NumberAnimation { duration: 120 } }
                            }
                            MouseArea {
                                id: appArea
                                property bool moved: false
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: board.dragging ? Qt.ClosedHandCursor : Qt.PointingHandCursor
                                onPressed: mouse => {
                                    moved = false;
                                    if (mouse.modifiers & Qt.ShiftModifier) {
                                        board.dragging = app.modelData;
                                        board.dragTo(mapToItem(board, mouse.x, mouse.y));
                                    }
                                }
                                onPositionChanged: mouse => {
                                    if (!board.dragging)
                                        return;
                                    moved = true;
                                    board.dragTo(mapToItem(board, mouse.x, mouse.y));
                                }
                                onReleased: {
                                    if (board.dragging)
                                        board.drop();
                                }
                                onClicked: mouse => {
                                    if (moved || (mouse.modifiers & Qt.ShiftModifier))
                                        return;
                                    Hyprland.dispatch(`hl.dsp.focus({ window = "address:${app.modelData.address}" })`);
                                    board.picked();
                                }
                                StyledToolTip {
                                    extraVisibleCondition: appArea.containsMouse && board.dragging === null
                                    text: `${app.modelData.title || app.modelData.class}\n${Translation.tr("Shift + drag to move it to another workspace")}`
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // The app in hand while it is moved.
    IconImage {
        visible: board.dragging !== null
        implicitSize: 48
        x: board.dragAt.x - 24
        y: board.dragAt.y - 24
        z: 10
        source: board.iconFor(board.dragging)
    }
}
