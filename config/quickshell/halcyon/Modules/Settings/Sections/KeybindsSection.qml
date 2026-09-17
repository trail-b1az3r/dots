import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.Config
import qs.Components
import qs.Services
import ".."

/**
 * Rebinding.
 *
 * Click a shortcut, press the keys you want, and it is written to
 * settings.json and regenerated into Hyprland's configuration — no file
 * editing, and no restart.
 */
ColumnLayout {
    id: root
    spacing: Theme.spacingLg

    property var catalog: ({})
    property string capturing: ""
    property string filter: ""

    FileView {
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

    readonly property var binds: {
        const all = root.catalog.binds ?? [];
        const overrides = Config.get("keybinds", ({}));
        const needle = root.filter.trim().toLowerCase();
        return all
            .map(bind => ({
                id: bind.id,
                title: bind.title,
                category: bind.category,
                keys: overrides[bind.id] ?? bind.default,
                changed: overrides[bind.id] !== undefined
            }))
            .filter(bind => needle.length === 0
                || bind.title.toLowerCase().indexOf(needle) >= 0
                || String(bind.keys).toLowerCase().indexOf(needle) >= 0);
    }

    /** Turn a key event into the string Hyprland's `hl.bind` expects. */
    function describe(event: var): string {
        const parts = [];
        if (event.modifiers & Qt.MetaModifier) parts.push("SUPER");
        if (event.modifiers & Qt.ControlModifier) parts.push("CTRL");
        if (event.modifiers & Qt.AltModifier) parts.push("ALT");
        if (event.modifiers & Qt.ShiftModifier) parts.push("SHIFT");

        const name = root.keyName(event.key);
        if (name.length === 0)
            return "";
        parts.push(name);
        return parts.join(" + ");
    }

    function keyName(key: int): string {
        // Modifier-only presses are not a shortcut yet.
        if (key === Qt.Key_Super_L || key === Qt.Key_Super_R
            || key === Qt.Key_Control || key === Qt.Key_Alt
            || key === Qt.Key_Shift || key === Qt.Key_Meta)
            return "";
        if (key >= Qt.Key_A && key <= Qt.Key_Z)
            return String.fromCharCode("A".charCodeAt(0) + (key - Qt.Key_A));
        if (key >= Qt.Key_0 && key <= Qt.Key_9)
            return String(key - Qt.Key_0);
        if (key >= Qt.Key_F1 && key <= Qt.Key_F12)
            return "F" + (1 + key - Qt.Key_F1);
        switch (key) {
        case Qt.Key_Space: return "Space";
        case Qt.Key_Return:
        case Qt.Key_Enter: return "Return";
        case Qt.Key_Tab: return "Tab";
        case Qt.Key_Escape: return "Escape";
        case Qt.Key_Left: return "left";
        case Qt.Key_Right: return "right";
        case Qt.Key_Up: return "up";
        case Qt.Key_Down: return "down";
        case Qt.Key_Comma: return "comma";
        case Qt.Key_Period: return "period";
        case Qt.Key_Slash: return "slash";
        case Qt.Key_Backslash: return "backslash";
        case Qt.Key_Minus: return "minus";
        case Qt.Key_Equal: return "equal";
        case Qt.Key_QuoteLeft: return "grave";
        case Qt.Key_BracketLeft: return "bracketleft";
        case Qt.Key_BracketRight: return "bracketright";
        case Qt.Key_Semicolon: return "semicolon";
        case Qt.Key_Apostrophe: return "apostrophe";
        default: return "";
        }
    }

    function assign(id: string, keys: string): void {
        const overrides = Object.assign({}, Config.get("keybinds", ({})));
        overrides[id] = keys;
        Config.set("keybinds", overrides);
        root.capturing = "";
    }

    function reset(id: string): void {
        const overrides = Object.assign({}, Config.get("keybinds", ({})));
        delete overrides[id];
        Config.set("keybinds", overrides);
    }

    SettingsGroup {
        title: "Shortcuts"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingSm

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spacingSm

                GlassField {
                    Layout.fillWidth: true
                    implicitHeight: 30
                    glyph: "󰍉"
                    placeholder: "Filter shortcuts"
                    onTextChanged: root.filter = text
                }

                GlassButton {
                    text: "Reset all"
                    onClicked: Config.set("keybinds", ({}))
                }
            }

            Label {
                Layout.fillWidth: true
                visible: root.capturing.length > 0
                text: "Press the new shortcut, or Escape to cancel."
                variant: "footnote"
                color: Theme.accentText
            }

            Repeater {
                model: root.binds

                RowLayout {
                    id: bindRow
                    required property var modelData

                    Layout.fillWidth: true
                    spacing: Theme.spacingMd

                    Label {
                        Layout.fillWidth: true
                        text: modelData.title
                        variant: "footnote"
                    }

                    Rectangle {
                        Layout.preferredWidth: 190
                        Layout.preferredHeight: 28
                        radius: Theme.radiusXs
                        color: root.capturing === modelData.id
                            ? Theme.surfaceSelected
                            : Theme.surfaceSunken
                        border.width: 1
                        border.color: root.capturing === modelData.id
                            ? Theme.accent
                            : Theme.glassBorder

                        Label {
                            anchors.centerIn: parent
                            text: root.capturing === modelData.id
                                ? "Press keys…"
                                : String(modelData.keys)
                            variant: "caption"
                            font.family: Theme.fontMono
                            tone: modelData.changed ? "accent" : "secondary"
                        }

                        StateLayer {
                            anchors.fill: parent
                            radius: Theme.radiusXs
                            focusVisible: capture.activeFocus
                            onClicked: {
                                root.capturing = modelData.id;
                                capture.forceActiveFocus();
                            }
                        }
                    }

                    GlassIconButton {
                        glyph: "󰑐"
                        size: 24
                        iconSize: 11
                        tooltip: "Reset"
                        visible: modelData.changed
                        onClicked: root.reset(modelData.id)
                    }
                }
            }
        }
    }

    // A focus sink that receives the key press while capturing. Using one
    // for the whole list avoids nineteen focus scopes competing.
    Item {
        id: capture
        focus: root.capturing.length > 0

        Keys.onPressed: event => {
            if (root.capturing.length === 0)
                return;
            if (event.key === Qt.Key_Escape) {
                root.capturing = "";
                event.accepted = true;
                return;
            }
            const combination = root.describe(event);
            if (combination.length > 0) {
                root.assign(root.capturing, combination);
                event.accepted = true;
            }
        }
    }
}
