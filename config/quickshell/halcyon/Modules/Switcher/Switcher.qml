import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Hyprland
import qs.Config
import qs.Components
import qs.Services

/**
 * The application switcher.
 *
 * Holding Super and tapping Tab walks the list most-recently-used first,
 * the way ⌘Tab does; releasing Super commits. Because Hyprland sends a
 * separate press for each tap rather than telling us when the modifier
 * goes up, the switcher commits on a short idle timer instead — long
 * enough to tap through a list, short enough to feel immediate.
 */
OverlayWindow {
    id: root

    name: "switcher"
    namespaceName: "halcyon-switcher"
    origin: "center"
    scrim: false
    grabKeyboard: false

    property int index: 0
    /** Snapshot taken when the switcher opens; the live order changes as
     *  soon as we focus something, which would make Tab unusable. */
    property var entries: []

    readonly property int commitDelay: 620

    function open(direction: int): void {
        if (!root.shown) {
            root.entries = root.collect();
            root.index = root.entries.length > 1 ? (direction > 0 ? 1 : root.entries.length - 1) : 0;
            Overlays.open(root.name, {});
        } else {
            root.step(direction);
        }
        commit.restart();
    }

    function step(direction: int): void {
        if (root.entries.length === 0)
            return;
        root.index = (root.index + direction + root.entries.length) % root.entries.length;
        commit.restart();
    }

    function accept(): void {
        const entry = root.entries[root.index];
        Overlays.close(root.name);
        if (entry)
            Workspaces.focusWindow(entry.address);
    }

    /** Most recently used first, with the focused window at the front. */
    function collect(): var {
        const active = Hyprland.activeToplevel;
        const all = Workspaces.toplevels.filter(
            toplevel => (toplevel.title ?? "").length > 0
        );
        const ordered = all.slice().sort((a, b) => {
            if (a === active) return -1;
            if (b === active) return 1;
            return 0;
        });
        return ordered.map(toplevel => ({
            address: toplevel.address,
            title: toplevel.title,
            appClass: String((toplevel.lastIpcObject ?? ({})).class ?? ""),
            workspace: toplevel.workspace?.name ?? ""
        }));
    }

    Timer {
        id: commit
        interval: root.commitDelay
        onTriggered: {
            if (root.shown)
                root.accept();
        }
    }

    Keys.onReturnPressed: root.accept()
    Keys.onEscapePressed: Overlays.close(root.name)

    GlassSurface {
        anchors.centerIn: parent
        width: Math.min(row.implicitWidth + padding * 2, root.width - Theme.spacingXl * 2)
        height: row.implicitHeight + padding * 2 + 26
        level: 4
        radius: Theme.radiusXl
        padding: Theme.panelPadding
        visible: root.entries.length > 0

        ColumnLayout {
            anchors.fill: parent
            spacing: Theme.spacingSm

            Row {
                id: row
                Layout.alignment: Qt.AlignHCenter
                spacing: Theme.spacingSm

                Repeater {
                    model: root.entries

                    Item {
                        required property int index
                        required property var modelData

                        width: 84
                        height: 84

                        Rectangle {
                            anchors.fill: parent
                            radius: Theme.radiusLg
                            color: index === root.index ? Theme.surfaceSelected : "transparent"
                            border.width: index === root.index ? 1 : 0
                            border.color: Theme.accent

                            Behavior on color {
                                enabled: Theme.animationsEnabled
                                ColorAnimation { duration: Theme.durInstant }
                            }
                        }

                        Icon {
                            anchors.centerIn: parent
                            source: modelData.appClass.toLowerCase()
                            glyph: "󰖯"
                            size: 48
                            color: Theme.textSecondary
                        }

                        StateLayer {
                            anchors.fill: parent
                            radius: Theme.radiusLg
                            onClicked: {
                                root.index = index;
                                root.accept();
                            }
                        }
                    }
                }
            }

            Label {
                Layout.fillWidth: true
                text: root.entries.length > 0
                    ? (root.entries[root.index]?.title ?? "")
                    : ""
                variant: "footnote"
                tone: "secondary"
                horizontalAlignment: Text.AlignHCenter
                elide: Text.ElideMiddle
            }
        }
    }
}
