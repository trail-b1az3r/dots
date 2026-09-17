import QtQuick
import QtQuick.Layouts
import Quickshell
import qs.Config
import qs.Components
import qs.Services

/**
 * Spotlight — the universal search field.
 *
 * Centred, glassy, and keyboard-first: the field has focus the moment it
 * opens, the arrow keys move through results without leaving the text,
 * and Enter runs the selected one. The list is grouped by category with
 * the best answer first, so an arithmetic result or a conversion sits
 * above the applications rather than competing with them.
 */
OverlayWindow {
    id: root

    name: "spotlight"
    namespaceName: "halcyon-spotlight"
    origin: "top"
    grabKeyboard: true

    readonly property int panelWidth: Math.min(720, root.width - Theme.spacingXl * 2)
    readonly property int maxListHeight: Math.min(440, root.height * 0.52)

    onOpened: {
        field.text = "";
        Search.clear();
        // A newly opened launcher with a stale list is disorienting.
        field.forceActiveFocus();
        const mode = Overlays.payload.mode ?? "";
        if (mode === "clipboard") {
            field.text = "";
            Search.searchProviders(["clipboard"]);
        } else if (mode === "ai") {
            field.text = "";
        }
    }

    Connections {
        target: Overlays
        function onRequested(name: string, action: string, args: var): void {
            if (name !== root.name)
                return;
            if (action === "prefill") {
                field.text = args.text ?? "";
                Search.search(field.text);
            }
        }
    }

    Item {
        anchors.fill: parent

        GlassSurface {
            id: panel

            anchors.horizontalCenter: parent.horizontalCenter
            y: Math.max(Theme.spacingXl, parent.height * 0.14)
            width: root.panelWidth
            height: column.implicitHeight + padding * 2
            level: 4
            radius: Theme.radiusXl
            padding: Theme.panelPaddingTight
            tintStrength: 1.1

            Behavior on height {
                enabled: Theme.animationsEnabled && !Theme.reducedMotion
                NumberAnimation {
                    duration: Theme.durQuick
                    easing.type: Easing.BezierSpline
                    easing.bezierCurve: Theme.easeStandard
                }
            }

            ColumnLayout {
                id: column
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                spacing: 0

                // ── Field ────────────────────────────────────────────

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 54
                    spacing: Theme.spacingMd

                    Icon {
                        Layout.leftMargin: Theme.spacingMd
                        glyph: "󰍉"
                        size: 22
                        color: Theme.textTertiary
                    }

                    TextInput {
                        id: field
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter

                        focus: true
                        color: Theme.text
                        selectionColor: Theme.accent
                        selectedTextColor: Theme.onAccent
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sizeTitle
                        clip: true

                        onTextChanged: Search.search(text)

                        Keys.onDownPressed: Search.move(1)
                        Keys.onUpPressed: Search.move(-1)
                        Keys.onReturnPressed: root.activate()
                        Keys.onEnterPressed: root.activate()
                        Keys.onEscapePressed: Overlays.close(root.name)
                        Keys.onTabPressed: Search.move(1)
                        Keys.onBacktabPressed: Search.move(-1)

                        Label {
                            anchors.verticalCenter: parent.verticalCenter
                            visible: field.text.length === 0
                            text: "Search applications, files, settings and more"
                            variant: "title"
                            tone: "tertiary"
                            font.weight: Theme.weightRegular
                        }
                    }

                    Spinner {
                        Layout.rightMargin: Theme.spacingMd
                        visible: Search.searching
                        size: 16
                    }

                    GlassIconButton {
                        Layout.rightMargin: Theme.spacingSm
                        visible: field.text.length > 0
                        glyph: "󰅖"
                        size: 26
                        iconSize: 14
                        tooltip: "Clear"
                        onClicked: {
                            field.text = "";
                            field.forceActiveFocus();
                        }
                    }
                }

                Separator {
                    Layout.fillWidth: true
                    visible: Search.results.length > 0
                }

                // ── Results ──────────────────────────────────────────

                ListView {
                    id: list
                    Layout.fillWidth: true
                    Layout.preferredHeight: Math.min(
                        root.maxListHeight,
                        contentHeight + Theme.spacingSm * 2
                    )
                    visible: Search.results.length > 0
                    clip: true
                    interactive: contentHeight > height
                    topMargin: Theme.spacingSm
                    bottomMargin: Theme.spacingSm
                    currentIndex: Search.selected
                    highlightFollowsCurrentItem: true
                    highlightMoveDuration: Theme.reducedMotion ? 0 : Theme.durInstant
                    boundsBehavior: Flickable.StopAtBounds

                    model: Search.results

                    // Keep the selection on screen when the arrow keys
                    // walk past the fold.
                    onCurrentIndexChanged: positionViewAtIndex(
                        currentIndex, ListView.Contain
                    )

                    delegate: Item {
                        required property int index
                        required property var modelData

                        width: list.width
                        height: header.visible ? row.height + header.height : row.height

                        readonly property bool startsCategory: {
                            if (index === 0)
                                return true;
                            const previous = Search.results[index - 1];
                            return previous.category !== modelData.category;
                        }

                        Label {
                            id: header
                            visible: parent.startsCategory
                            height: visible ? 24 : 0
                            x: Theme.spacingMd
                            text: modelData.category ?? ""
                            variant: "caption"
                            tone: "tertiary"
                            font.weight: Theme.weightSemibold
                        }

                        ListRow {
                            id: row
                            y: header.height
                            width: parent.width
                            title: modelData.title ?? ""
                            subtitle: modelData.subtitle ?? ""
                            icon: modelData.icon ?? ""
                            glyph: root.glyphFor(modelData)
                            selected: index === Search.selected
                            onActivated: {
                                Search.selected = index;
                                root.activate();
                            }
                        }
                    }
                }

                // ── Empty state ──────────────────────────────────────

                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 84
                    visible: field.text.length > 0
                        && Search.results.length === 0
                        && !Search.searching

                    Column {
                        anchors.centerIn: parent
                        spacing: Theme.spacingXs

                        Label {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "No results"
                            variant: "bodyLarge"
                            tone: "secondary"
                        }

                        Label {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "Press Enter to ask the assistant"
                            variant: "footnote"
                            tone: "tertiary"
                            visible: Config.get("assistant.enabled", true)
                        }
                    }
                }

                // ── Hints ────────────────────────────────────────────

                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 30
                    visible: Search.results.length > 0

                    Row {
                        anchors.right: parent.right
                        anchors.rightMargin: Theme.spacingMd
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: Theme.spacingMd

                        Label {
                            text: "↑↓ to move"
                            variant: "caption"
                            tone: "tertiary"
                        }
                        Label {
                            text: "↵ to open"
                            variant: "caption"
                            tone: "tertiary"
                        }
                        Label {
                            text: "esc to close"
                            variant: "caption"
                            tone: "tertiary"
                        }
                    }
                }
            }
        }
    }

    function activate(): void {
        if (Search.results.length === 0) {
            // Nothing matched: hand the query to the assistant rather than
            // doing nothing at all.
            if (field.text.trim().length > 0 && Config.get("assistant.enabled", true)) {
                Assistant.ask(field.text);
                Overlays.open("assistant", {});
            }
            return;
        }
        Search.activate(-1);
        Overlays.close(root.name);
    }

    function glyphFor(result: var): string {
        switch (result.provider ?? "") {
        case "calculator": return "󰪚";
        case "units": return "󰬲";
        case "settings": return "󰒓";
        case "actions": return "󰐍";
        case "power": return "󰁹";
        case "windows": return "󰖯";
        case "clipboard": return "󰅇";
        case "recent": return "󰋚";
        case "commands": return "󰆍";
        case "web": return "󰖟";
        case "assistant": return "󰚩";
        case "hypernix": return "󰆧";
        case "files": return "󰈙";
        default: return "󰘔";
        }
    }
}
