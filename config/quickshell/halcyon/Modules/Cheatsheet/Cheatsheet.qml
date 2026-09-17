import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.Config
import qs.Components
import qs.Services

/**
 * The keyboard shortcut reference.
 *
 * Reads the same catalog the generated Hyprland binds come from, layered
 * with the user's overrides, so it can never disagree with what the keys
 * actually do. Typing filters it.
 */
OverlayWindow {
    id: root

    name: "cheatsheet"
    namespaceName: "halcyon-overlay"
    origin: "center"
    grabKeyboard: true

    property var catalog: ({})
    property string filter: ""

    onOpened: {
        root.filter = "";
        if (!root.catalog.binds)
            reader.reload();
        search.forceActiveFocus();
    }

    FileView {
        id: reader
        path: Paths.dataHome + "/halcyon/keybinds.catalog.json"
        printErrors: false
        onLoaded: {
            try {
                root.catalog = JSON.parse(this.text());
            } catch (error) {
                root.catalog = ({});
            }
        }
    }

    /** Catalog defaults with settings.json overrides applied. */
    readonly property var sections: {
        const binds = root.catalog.binds ?? [];
        const categories = root.catalog.categories ?? [];
        const overrides = Config.get("keybinds", ({}));
        const needle = root.filter.trim().toLowerCase();

        return categories.map(category => {
            const items = binds
                .filter(bind => bind.category === category.id)
                .map(bind => ({
                    title: bind.title,
                    keys: overrides[bind.id] ?? bind.default
                }))
                .filter(bind => bind.keys && bind.keys.length > 0)
                .filter(bind => needle.length === 0
                    || bind.title.toLowerCase().indexOf(needle) >= 0
                    || bind.keys.toLowerCase().indexOf(needle) >= 0);
            return { title: category.title, items: items };
        }).filter(section => section.items.length > 0);
    }

    GlassSurface {
        anchors.centerIn: parent
        width: Math.min(880, root.width - Theme.spacingXl * 2)
        height: Math.min(640, root.height - Theme.spacingXl * 2)
        level: 4
        radius: Theme.radiusXl
        padding: Theme.panelPadding

        ColumnLayout {
            anchors.fill: parent
            spacing: Theme.spacingMd

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spacingMd

                Label {
                    text: "Keyboard Shortcuts"
                    variant: "title"
                }

                Item { Layout.fillWidth: true }

                GlassField {
                    id: search
                    Layout.preferredWidth: 240
                    implicitHeight: 32
                    glyph: "󰍉"
                    placeholder: "Filter"
                    onTextChanged: root.filter = text
                    onEscaped: Overlays.close(root.name)
                }
            }

            Separator { Layout.fillWidth: true }

            Flickable {
                Layout.fillWidth: true
                Layout.fillHeight: true
                contentHeight: grid.implicitHeight
                clip: true
                boundsBehavior: Flickable.StopAtBounds

                GridLayout {
                    id: grid
                    width: parent.width
                    columns: 2
                    columnSpacing: Theme.spacingXl
                    rowSpacing: Theme.spacingLg

                    Repeater {
                        model: root.sections

                        ColumnLayout {
                            required property var modelData
                            Layout.fillWidth: true
                            Layout.alignment: Qt.AlignTop
                            spacing: 2

                            Label {
                                text: modelData.title
                                variant: "caption"
                                tone: "tertiary"
                                font.weight: Theme.weightSemibold
                            }

                            Repeater {
                                model: modelData.items

                                RowLayout {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    spacing: Theme.spacingMd

                                    Label {
                                        Layout.fillWidth: true
                                        text: modelData.title
                                        variant: "footnote"
                                    }

                                    Row {
                                        spacing: 3

                                        Repeater {
                                            model: String(modelData.keys).split("+")

                                            Rectangle {
                                                required property var modelData

                                                height: 20
                                                width: keyLabel.implicitWidth + 12
                                                radius: Theme.radiusXs
                                                color: Theme.surfaceRaised
                                                border.width: 1
                                                border.color: Theme.glassBorder

                                                Label {
                                                    id: keyLabel
                                                    anchors.centerIn: parent
                                                    text: String(modelData).trim()
                                                    variant: "caption"
                                                    tone: "secondary"
                                                    font.family: Theme.fontMono
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Label {
                Layout.fillWidth: true
                visible: root.sections.length === 0
                text: root.catalog.binds
                    ? "Nothing matches that."
                    : "The shortcut catalog could not be read — re-run ./install.sh."
                variant: "footnote"
                tone: "tertiary"
                horizontalAlignment: Text.AlignHCenter
            }
        }
    }
}
