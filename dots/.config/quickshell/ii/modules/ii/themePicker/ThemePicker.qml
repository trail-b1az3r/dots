import qs
import qs.services
import qs.modules.common
import qs.modules.common.widgets
import qs.modules.common.functions
import "../background/widgets/revolver/RevolverStyles.js" as Styles
import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Hyprland

/**
 * The theme picker (Ctrl + Super + Shift + T, or `halcyon theme menu`): every Halcyon theme as a card with its
 * wallpaper, its colours and its own dock frame, over the dimmed screen. Arrows or the mouse to choose, Enter or a
 * click to apply, Esc to close. Below the cards: "follow the wallpaper" and the effects level. The themes come in
 * pages, as many rows as the screen has room for: PgUp/PgDn, the mouse wheel or the dots turn them, and the arrows
 * cross from one page to the next.
 *
 * The list comes from `halcyon-theme list --json`; the pictures are small previews `halcyon-theme previews` makes
 * from each wallpaper (a video's first frame), made in the background the first time.
 */
Scope {
    id: root

    property bool open: false
    property var themes: []
    property string current: ""
    property string effects: ""
    property int selected: 0
    // The first list after opening selects the active theme; later ones (previews made in the background) keep what
    // you selected. Previews are tried once per opening: one that cannot be made (a video without ffmpeg) used to
    // list and make previews again and again, putting the selection back on the active theme each time.
    property bool fresh: true
    property bool previewsTried: false
    readonly property string tool: `${FileUtils.trimFileProtocol(Directories.config)}/hypr/hyprland/halcyon/halcyon-theme`
    property var focusedScreen: Quickshell.screens.find(s => s.name === Hyprland.focusedMonitor?.name) ?? Quickshell.screens[0]

    function show() {
        root.fresh = true;
        root.previewsTried = false;
        listProc.running = true;
        root.open = true;
    }
    function toggle() {
        if (root.open)
            root.open = false;
        else
            root.show();
    }
    function apply(themeId) {
        root.open = false;
        if (themeId === "")
            Quickshell.execDetached([root.tool, "off"]);
        else
            Quickshell.execDetached([root.tool, "apply", themeId]);
    }

    Process {
        id: listProc
        command: [root.tool, "list", "--json"]
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const data = JSON.parse(this.text);
                    const kept = root.fresh ? "" : (root.themes[root.selected]?.id ?? "");
                    root.themes = data.themes ?? [];
                    root.current = data.current ?? "";
                    root.effects = data.effects ?? "";
                    const at = kept !== "" ? root.themes.findIndex(t => t.id === kept) : root.themes.findIndex(t => t.active);
                    root.selected = Math.max(0, at);
                    root.fresh = false;
                    // Make the missing previews (once), then list again to show them.
                    if (!root.previewsTried && root.themes.some(t => t.has_wallpaper && t.preview === "") && !previewProc.running) {
                        root.previewsTried = true;
                        previewProc.running = true;
                    }
                } catch (error) {
                    root.themes = [];
                }
            }
        }
    }
    Process {
        id: previewProc
        command: [root.tool, "previews"]
        onExited: if (root.open) listProc.running = true
    }

    Loader {
        active: root.open
        sourceComponent: PanelWindow {
            id: panel
            screen: root.focusedScreen
            color: "transparent"
            WlrLayershell.namespace: "quickshell:themePicker"
            WlrLayershell.layer: WlrLayer.Overlay
            WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive
            exclusionMode: ExclusionMode.Ignore
            anchors {
                top: true
                bottom: true
                left: true
                right: true
            }

            // The screen, dimmed; a click outside the cards closes.
            Rectangle {
                id: scrim
                anchors.fill: parent
                color: Qt.rgba(0, 0, 0, 0.55)
                opacity: 0
                Component.onCompleted: opacity = 1
                Behavior on opacity {
                    NumberAnimation { duration: 180; easing.type: Easing.OutCubic }
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: root.open = false
                }
            }

            Item {
                id: content
                anchors.centerIn: parent
                width: Math.min(parent.width - 80, grid.columns * 316 + 48)
                height: column.implicitHeight + 48
                focus: true
                scale: 0.96
                opacity: 0
                Component.onCompleted: {
                    scale = 1;
                    opacity = 1;
                    forceActiveFocus();
                }
                Behavior on scale {
                    NumberAnimation { duration: 240; easing.type: Easing.OutBack; easing.overshoot: 1.2 }
                }
                Behavior on opacity {
                    NumberAnimation { duration: 180 }
                }

                Keys.onPressed: event => {
                    const n = root.themes.length;
                    if (n === 0 && event.key !== Qt.Key_Escape)
                        return;
                    if (event.key === Qt.Key_Escape) {
                        root.open = false;
                    } else if (event.key === Qt.Key_Right || event.key === Qt.Key_Tab) {
                        root.selected = (root.selected + 1) % n;
                    } else if (event.key === Qt.Key_Left || event.key === Qt.Key_Backtab) {
                        root.selected = (root.selected - 1 + n) % n;
                    } else if (event.key === Qt.Key_Down) {
                        root.selected = Math.min(n - 1, root.selected + grid.columns);
                    } else if (event.key === Qt.Key_Up) {
                        root.selected = Math.max(0, root.selected - grid.columns);
                    } else if (event.key === Qt.Key_PageDown || event.key === Qt.Key_BracketRight) {
                        content.turn(1);
                    } else if (event.key === Qt.Key_PageUp || event.key === Qt.Key_BracketLeft) {
                        content.turn(-1);
                    } else if (event.key === Qt.Key_Home) {
                        root.selected = 0;
                    } else if (event.key === Qt.Key_End) {
                        root.selected = n - 1;
                    } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                        if (root.themes[root.selected])
                            root.apply(root.themes[root.selected].id);
                    } else {
                        return;
                    }
                    event.accepted = true;
                }

                // Pages: as many rows of cards as fit on the screen (two or three), the page the selected card is on.
                readonly property int rows: Math.max(1, Math.min(3, Math.floor((panel.height - 300) / 212)))
                readonly property int perPage: Math.max(1, grid.columns * rows)
                readonly property int pages: Math.max(1, Math.ceil(root.themes.length / perPage))
                readonly property int page: Math.min(pages - 1, Math.floor(root.selected / perPage))
                function turn(by) {
                    const p = Math.max(0, Math.min(pages - 1, page + by));
                    if (p !== page)
                        root.selected = Math.min(root.themes.length - 1, p * perPage + root.selected % perPage);
                }

                MouseArea {
                    anchors.fill: parent    // keeps clicks between the cards from closing it
                    onWheel: wheel => {
                        const d = wheel.angleDelta.y !== 0 ? wheel.angleDelta.y : -wheel.angleDelta.x;
                        if (Math.abs(d) >= 60)
                            content.turn(d < 0 ? 1 : -1);
                    }
                }

                Rectangle {
                    anchors.fill: parent
                    radius: Appearance.rounding.windowRounding
                    color: ColorUtils.applyAlpha(Appearance.colors.colLayer0, 0.92)
                    border.width: 1
                    border.color: ColorUtils.applyAlpha(Appearance.colors.colOnLayer0, 0.08)
                }

                ColumnLayout {
                    id: column
                    anchors.fill: parent
                    anchors.margins: 24
                    spacing: 18

                    RowLayout {
                        Layout.fillWidth: true
                        StyledText {
                            text: Translation.tr("Themes")
                            font.pixelSize: Appearance.font.pixelSize.huge
                            font.weight: Font.DemiBold
                            color: Appearance.colors.colOnLayer0
                        }
                        StyledText {
                            Layout.fillWidth: true
                            Layout.leftMargin: 12
                            text: content.pages > 1
                                ? Translation.tr("← → ↑ ↓ to choose, PgUp PgDn for pages, Enter to apply, Esc to close")
                                : Translation.tr("← → ↑ ↓ to choose, Enter to apply, Esc to close")
                            font.pixelSize: Appearance.font.pixelSize.small
                            color: Appearance.colors.colSubtext
                        }
                    }

                    GridLayout {
                        id: grid
                        Layout.fillWidth: true
                        columns: Math.max(1, Math.min(4, Math.floor((panel.width - 128) / 316)))
                        columnSpacing: 16
                        rowSpacing: 16

                        Repeater {
                            model: root.themes.slice(content.page * content.perPage, (content.page + 1) * content.perPage)
                            delegate: ThemeCard {
                                required property var modelData
                                required property int index
                                readonly property int absIndex: content.page * content.perPage + index
                                theme: modelData
                                selected: absIndex === root.selected
                                onHovered: root.selected = absIndex
                                onChosen: root.apply(modelData.id)
                            }
                        }
                        // Keep the last page as tall as the others, so the window doesn't jump between pages.
                        Repeater {
                            model: content.pages > 1 ? Math.max(0, content.perPage - Math.min(content.perPage, root.themes.length - content.page * content.perPage)) : 0
                            delegate: Item {
                                Layout.preferredWidth: 300
                                Layout.preferredHeight: 196
                            }
                        }
                    }

                    // The pages: back, a dot each (the current one long), forward.
                    RowLayout {
                        Layout.alignment: Qt.AlignHCenter
                        visible: content.pages > 1
                        spacing: 10
                        RippleButton {
                            implicitWidth: 32
                            implicitHeight: 32
                            buttonRadius: 16
                            enabled: content.page > 0
                            opacity: enabled ? 1 : 0.35
                            onClicked: content.turn(-1)
                            contentItem: MaterialSymbol {
                                horizontalAlignment: Text.AlignHCenter
                                text: "chevron_left"
                                iconSize: Appearance.font.pixelSize.larger
                                color: Appearance.colors.colOnLayer0
                            }
                        }
                        Repeater {
                            model: content.pages
                            delegate: Rectangle {
                                required property int index
                                Layout.preferredWidth: index === content.page ? 24 : 8
                                Layout.preferredHeight: 8
                                radius: 4
                                color: index === content.page ? Appearance.colors.colPrimary
                                                              : ColorUtils.applyAlpha(Appearance.colors.colOnLayer0, 0.25)
                                Behavior on Layout.preferredWidth {
                                    NumberAnimation { duration: 180; easing.type: Easing.OutCubic }
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    anchors.margins: -6
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: content.turn(parent.index - content.page)
                                }
                            }
                        }
                        RippleButton {
                            implicitWidth: 32
                            implicitHeight: 32
                            buttonRadius: 16
                            enabled: content.page < content.pages - 1
                            opacity: enabled ? 1 : 0.35
                            onClicked: content.turn(1)
                            contentItem: MaterialSymbol {
                                horizontalAlignment: Text.AlignHCenter
                                text: "chevron_right"
                                iconSize: Appearance.font.pixelSize.larger
                                color: Appearance.colors.colOnLayer0
                            }
                        }
                    }

                    // Off, and the effects level.
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        RippleButtonWithIcon {
                            materialIcon: "wallpaper"
                            mainText: Translation.tr("Follow the wallpaper")
                            onClicked: root.apply("")
                        }
                        Item { Layout.fillWidth: true }
                        StyledText {
                            visible: root.current !== ""
                            text: Translation.tr("Effects")
                            color: Appearance.colors.colSubtext
                        }
                        Repeater {
                            model: root.current !== "" ? [
                                { value: "full", label: Translation.tr("Full"), icon: "auto_awesome" },
                                { value: "light", label: Translation.tr("Light"), icon: "blur_on" },
                                { value: "off", label: Translation.tr("Off"), icon: "block" }
                            ] : []
                            delegate: RippleButtonWithIcon {
                                required property var modelData
                                materialIcon: modelData.icon
                                mainText: modelData.label
                                toggled: root.effects === modelData.value
                                onClicked: {
                                    root.effects = modelData.value;
                                    Quickshell.execDetached([root.tool, "effects", modelData.value]);
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // One theme: its wallpaper, a shade for the text, its name and colours, its dock frame, a mark when active.
    component ThemeCard: Item {
        id: card
        property var theme: ({})
        property bool selected: false
        signal hovered
        signal chosen

        Layout.preferredWidth: 300
        Layout.preferredHeight: 196
        scale: selected ? 1.0 : 0.97
        Behavior on scale {
            NumberAnimation { duration: 160; easing.type: Easing.OutCubic }
        }

        readonly property color bg: card.theme.colors?.background ?? "#111111"
        readonly property color fg: card.theme.colors?.on_background ?? "#ffffff"
        readonly property color accent: card.theme.colors?.primary ?? "#ffffff"

        Rectangle {
            id: frame
            anchors.fill: parent
            radius: 16
            color: card.bg
            clip: true
            border.width: card.selected ? 2 : 1
            border.color: card.selected ? card.accent : ColorUtils.applyAlpha(card.fg, 0.12)

            Image {
                anchors.fill: parent
                anchors.margins: frame.border.width
                source: card.theme.preview ? "file://" + card.theme.preview : ""
                fillMode: Image.PreserveAspectCrop
                asynchronous: true
                sourceSize.width: 600
                visible: status === Image.Ready
                opacity: card.selected ? 1 : 0.82
                Behavior on opacity {
                    NumberAnimation { duration: 160 }
                }
            }
            // Without a wallpaper yet: the theme's colours in a gradient.
            Rectangle {
                anchors.fill: parent
                anchors.margins: frame.border.width
                visible: !card.theme.preview
                radius: frame.radius
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: card.bg }
                    GradientStop { position: 1.0; color: Qt.darker(card.accent, 2.4) }
                }
            }
            // A shade under the text.
            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.margins: frame.border.width
                height: 92
                radius: frame.radius
                gradient: Gradient {
                    GradientStop { position: 0.0; color: ColorUtils.applyAlpha(card.bg, 0) }
                    GradientStop { position: 0.55; color: ColorUtils.applyAlpha(card.bg, 0.86) }
                    GradientStop { position: 1.0; color: ColorUtils.applyAlpha(card.bg, 0.96) }
                }
            }

            // The theme's own dock frame, small, at the top left: each theme draws it differently.
            Loader {
                x: 12
                y: 12
                width: 86
                height: 22
                active: Styles.frameKindFor(card.theme.id ?? "") !== ""
                source: "../dock/DockFrame.qml"
                onLoaded: {
                    item.kind = Qt.binding(() => Styles.frameKindFor(card.theme.id ?? ""));
                    item.colBase = Qt.binding(() => card.bg);
                    item.colAccent = Qt.binding(() => card.accent);
                    item.colAccent2 = Qt.binding(() => card.theme.colors?.tertiary ?? card.accent);
                    item.colGlow = Qt.binding(() => card.accent);
                }
            }

            // Active.
            Rectangle {
                visible: card.theme.active ?? false
                anchors.top: parent.top
                anchors.right: parent.right
                anchors.margins: 10
                width: activeLabel.implicitWidth + 16
                height: 22
                radius: 11
                color: card.accent
                StyledText {
                    id: activeLabel
                    anchors.centerIn: parent
                    text: Translation.tr("In use")
                    font.pixelSize: Appearance.font.pixelSize.smaller
                    font.weight: Font.DemiBold
                    color: card.bg
                }
            }

            ColumnLayout {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.margins: 14
                spacing: 4
                RowLayout {
                    Layout.fillWidth: true
                    StyledText {
                        Layout.fillWidth: true
                        text: card.theme.name ?? ""
                        color: card.fg
                        font.pixelSize: Appearance.font.pixelSize.larger
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }
                    // The palette.
                    Repeater {
                        model: ["primary", "secondary", "tertiary"]
                        Rectangle {
                            required property string modelData
                            width: 12
                            height: 12
                            radius: 6
                            color: card.theme.colors?.[modelData] ?? "transparent"
                            border.width: 1
                            border.color: ColorUtils.applyAlpha(card.fg, 0.3)
                        }
                    }
                }
                StyledText {
                    Layout.fillWidth: true
                    text: (card.theme.description ?? "").split(". ")[0]
                    color: ColorUtils.applyAlpha(card.fg, 0.72)
                    font.pixelSize: Appearance.font.pixelSize.smaller
                    elide: Text.ElideRight
                }
            }
        }

        MouseArea {
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            // Real pointer movement only: a card that slides in under a still pointer (a new page) does not take the
            // selection from the keyboard.
            onPositionChanged: card.hovered()
            onClicked: card.chosen()
        }
    }

    IpcHandler {
        target: "themePicker"
        function toggle(): void {
            root.toggle();
        }
        function open(): void {
            root.show();
        }
        function close(): void {
            root.open = false;
        }
    }

    GlobalShortcut {
        name: "themePickerToggle"
        description: "Opens the theme picker"
        onPressed: root.toggle()
    }
}
