import QtQuick
import Quickshell.Hyprland
import qs.Config
import qs.Services
import "../"

/**
 * Workspace indicators for the monitor this bar is on.
 *
 * Slots are fixed, so the row does not resize as workspaces come and
 * go — a bar whose left edge moves every time you open a window is
 * unusable as a pointer target. Empty slots are dimmed rather than
 * removed.
 *
 * With `workspaces.perMonitor`, only workspaces belonging to this
 * bar's screen are shown, which is the whole reason the bar knows what
 * screen it is on.
 */
Item {
    id: root

    property var hostBar: null

    readonly property var screenName: root.hostBar && root.hostBar.barScreen
        ? root.hostBar.barScreen.name : ""

    readonly property var visibleSlots: {
        const slots = Workspaces.slots;
        if (!Workspaces.perMonitor || !root.screenName) {
            return slots;
        }
        // A slot with no live workspace has no monitor yet; show it on
        // every bar rather than hiding the numbers people navigate by.
        return slots.filter(slot => !slot.exists || slot.monitor === ""
            || slot.monitor === root.screenName);
    }

    implicitWidth: row.implicitWidth
    implicitHeight: parent ? parent.height : 0

    Row {
        id: row

        anchors.verticalCenter: parent.verticalCenter
        spacing: Theme.spacingXxs

        Repeater {
            model: root.visibleSlots

            delegate: Item {
                id: slotItem

                required property var modelData
                readonly property var slot: slotItem.modelData

                width: slotItem.slot.focused ? Theme.spacingXl : Theme.spacingLg
                height: Theme.spacingMd

                Behavior on width {
                    enabled: Theme.animationsEnabled
                    NumberAnimation {
                        duration: Theme.durQuick
                        easing.type: Easing.Bezier
                        easing.bezierCurve: Theme.curve("emphasised")
                    }
                }

                Rectangle {
                    id: pill

                    anchors.centerIn: parent
                    width: parent.width
                    height: Theme.spacingSm
                    radius: height / 2
                    color: {
                        if (slotItem.slot.urgent) {
                            return Theme.danger;
                        }
                        if (slotItem.slot.focused) {
                            return Theme.accent;
                        }
                        if (slotItem.slot.occupied) {
                            return Qt.rgba(Theme.text.r, Theme.text.g,
                                           Theme.text.b, 0.55);
                        }
                        return Qt.rgba(Theme.text.r, Theme.text.g,
                                       Theme.text.b, 0.18);
                    }

                    Behavior on color {
                        enabled: Theme.animationsEnabled
                        ColorAnimation {
                            duration: Theme.durQuick
                        }
                    }
                }

                HoverHandler {
                    id: slotHover

                    cursorShape: Qt.PointingHandCursor
                }

                // Published to the bar's shared tooltip while hovered.
                readonly property string slotTooltip: {
                    if (!slotHover.hovered) {
                        return "";
                    }
                    const name = slotItem.slot.name;
                    if (slotItem.slot.windows > 0) {
                        return qsTr("Workspace %1 · %n window(s)", "",
                                    slotItem.slot.windows).arg(name);
                    }
                    return qsTr("Workspace %1 · empty").arg(name);
                }

                TapHandler {
                    acceptedButtons: Qt.LeftButton | Qt.RightButton
                    onTapped: (point, button) => {
                        if (button === Qt.RightButton) {
                            Workspaces.moveWindowTo(slotItem.slot.id);
                        } else {
                            Workspaces.focus(slotItem.slot.id);
                        }
                    }
                }
            }
        }
    }

    // The hovered slot's description, read back out of the repeater so
    // it cannot go stale when workspaces change underneath it.
    tooltip: {
        for (let index = 0; index < row.children.length; index++) {
            const child = row.children[index];
            if (child && child.slotTooltip) {
                return child.slotTooltip;
            }
        }
        return "";
    }

    WheelHandler {
        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
        onWheel: event => {
            const slots = root.visibleSlots;
            if (slots.length === 0) {
                return;
            }
            const current = slots.findIndex(slot => slot.focused);
            const step = event.angleDelta.y > 0 ? -1 : 1;
            let next = (current < 0 ? 0 : current + step);
            if (Config.get("workspaces.wrapAround", false)) {
                next = (next + slots.length) % slots.length;
            } else {
                next = Math.max(0, Math.min(slots.length - 1, next));
            }
            Workspaces.focus(slots[next].id);
        }
    }
}
