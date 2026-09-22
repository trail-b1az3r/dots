import QtQuick
import Quickshell
import Quickshell.Services.SystemTray
import qs.Config
import qs.Services
import qs.Components

/**
 * Status icons from running applications.
 *
 * Left-click activates, right-click asks the item for its menu, middle
 * click is the secondary activation some applications implement. An
 * item that provides no menu simply does not open one, rather than
 * opening an empty one.
 */
Item {
    id: root

    property var hostBar: null

    readonly property var items: SystemTray.items.values

    implicitWidth: row.implicitWidth
    implicitHeight: parent ? parent.height : 0
    visible: root.items.length > 0

    readonly property string tooltip: {
        for (let index = 0; index < row.children.length; index++) {
            const child = row.children[index];
            if (child && child.itemTooltip) {
                return child.itemTooltip;
            }
        }
        return "";
    }

    Row {
        id: row

        anchors.verticalCenter: parent.verticalCenter
        spacing: Theme.spacingXs

        Repeater {
            model: root.items

            delegate: Item {
                id: entry

                required property var modelData
                readonly property var item: entry.modelData

                width: Theme.sizeBodyLarge
                height: Theme.sizeBodyLarge

                readonly property string itemTooltip: entryHover.hovered
                    ? (entry.item.tooltipTitle || entry.item.title || "")
                    : ""

                Icon {
                    anchors.fill: parent
                    source: entry.item.icon
                    glyph: "\udb80\udd3b"
                    size: parent.width
                    color: Theme.textSecondary
                }

                HoverHandler {
                    id: entryHover

                    cursorShape: Qt.PointingHandCursor
                }

                TapHandler {
                    acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
                    onTapped: (point, button) => {
                        if (button === Qt.RightButton) {
                            if (entry.item.hasMenu) {
                                entry.item.display(root, entry.x, root.height);
                            }
                        } else if (button === Qt.MiddleButton) {
                            entry.item.secondaryActivate();
                        } else {
                            entry.item.activate();
                        }
                    }
                }
            }
        }
    }
}
