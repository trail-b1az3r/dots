import qs
import qs.services
import qs.modules.common
import qs.modules.common.widgets
import qs.modules.common.functions
import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Wayland
import Quickshell.Hyprland

// Hypr mode (halcyon/modes.lua): when the "hypr" submap starts, a band of light swipes across the screen, then the
// mode's binds appear. They stay until the mode ends. Clicks go through to the windows underneath, except on the card.
Scope {
    id: root

    readonly property string modeName: "hypr"
    property bool modeActive: false
    // Kept true while the exit animation runs, so the window outlives the mode by a moment.
    property bool shown: false

    property var focusedScreen: Quickshell.screens.find(s => s.name === Hyprland.focusedMonitor?.name)

    // The mode's own binds: those registered in its submap, with a description. The toggle is universal and lives
    // in the submap too, so it is left out by name.
    readonly property var modeBinds: HyprlandKeybinds.keybinds.filter(b => (b.submap === root.modeName || (b.description ?? "").startsWith("Hypr mode:")) && (b.description ?? "").length > 0 && !(b.description ?? "").includes("Toggle hypr mode"))

    function chordKeys(bind) {
        const keys = [];
        if (bind.modmask & (1 << 2)) keys.push("Ctrl");
        if (bind.modmask & (1 << 6)) keys.push("Super");
        if (bind.modmask & (1 << 0)) keys.push("Shift");
        if (bind.modmask & (1 << 3)) keys.push("Alt");
        const symbols = { "Left": "←", "Right": "→", "Up": "↑", "Down": "↓", "Return": "Enter", "Escape": "Esc", "Super": "" };
        keys.push(bind.key);
        return keys.map(k => symbols[k] !== undefined && symbols[k] !== "" ? symbols[k] : k);
    }

    Connections {
        target: Hyprland
        function onRawEvent(event) {
            if (event.name !== "submap")
                return;
            const entered = event.data === root.modeName;
            if (entered === root.modeActive)
                return;
            root.modeActive = entered;
            if (entered) {
                hideTimer.stop();
                root.shown = true;
            } else {
                hideTimer.restart();
            }
        }
    }

    Timer {
        id: hideTimer
        interval: 260
        onTriggered: root.shown = false
    }

    Loader {
        id: loader
        active: root.shown

        sourceComponent: PanelWindow {
            id: panel
            screen: root.focusedScreen
            color: "transparent"
            visible: true

            WlrLayershell.namespace: "quickshell:hyprMode"
            WlrLayershell.layer: WlrLayer.Overlay
            exclusionMode: ExclusionMode.Ignore
            exclusiveZone: 0
            anchors {
                top: true
                bottom: true
                left: true
                right: true
            }
            // Only the card takes input; everything else passes through to the windows.
            mask: Region {
                item: card
            }

            // The swipe: a soft band of the accent colour crossing the screen from left to right.
            Rectangle {
                id: band
                width: panel.width * 0.42
                height: panel.height
                y: 0
                x: -width
                opacity: 0
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: "transparent" }
                    GradientStop { position: 0.5; color: ColorUtils.applyAlpha(Appearance.m3colors.m3primary, 0.30) }
                    GradientStop { position: 1.0; color: "transparent" }
                }
            }

            // A thin bright edge riding at the front of the band.
            Rectangle {
                id: bandEdge
                width: 3
                height: panel.height
                x: band.x + band.width * 0.62
                opacity: band.opacity
                color: ColorUtils.applyAlpha(Appearance.m3colors.m3primary, 0.85)
            }

            SequentialAnimation {
                id: swipe
                running: root.modeActive
                ParallelAnimation {
                    NumberAnimation { target: band; property: "opacity"; from: 0; to: 1; duration: 90 }
                    NumberAnimation { target: band; property: "x"; from: -band.width; to: panel.width; duration: 520; easing.type: Easing.InOutCubic }
                }
                NumberAnimation { target: band; property: "opacity"; to: 0; duration: 80 }
                ScriptAction { script: { card.state = "shown"; card.playKeys(); } }
            }

            Rectangle {
                id: card
                state: "hidden"
                anchors.horizontalCenter: parent.horizontalCenter
                y: parent.height * 0.12
                implicitWidth: cardColumn.implicitWidth + 36
                implicitHeight: cardColumn.implicitHeight + 28
                radius: Appearance.rounding.large
                color: Appearance.colors.colLayer0
                border.width: 1
                border.color: ColorUtils.applyAlpha(Appearance.m3colors.m3primary, 0.55)

                function playKeys() {
                    for (let i = 0; i < bindRepeater.count; i++) {
                        const line = bindRepeater.itemAt(i);
                        if (line) line.play(140 + i * 90);
                    }
                }

                states: [
                    State {
                        name: "hidden"
                        PropertyChanges { target: card; opacity: 0; scale: 0.94 }
                    },
                    State {
                        name: "shown"
                        PropertyChanges { target: card; opacity: 1; scale: 1 }
                    }
                ]
                transitions: Transition {
                    NumberAnimation { properties: "opacity,scale"; duration: 220; easing.type: Easing.OutCubic }
                }

                Connections {
                    target: root
                    function onModeActiveChanged() {
                        if (!root.modeActive)
                            card.state = "hidden";
                    }
                }

                StyledRectangularShadow {
                    target: card
                    z: -1
                }

                ColumnLayout {
                    id: cardColumn
                    anchors.centerIn: parent
                    spacing: 10

                    RowLayout {
                        spacing: 10
                        MaterialSymbol {
                            text: "keyboard_command_key"
                            iconSize: Appearance.font.pixelSize.huge
                            color: Appearance.m3colors.m3primary
                        }
                        StyledText {
                            text: "Hypr mode"
                            font.pixelSize: Appearance.font.pixelSize.title
                            color: Appearance.colors.colOnLayer0
                        }
                        Item { Layout.fillWidth: true }
                        StyledText {
                            text: "Esc to leave"
                            font.pixelSize: Appearance.font.pixelSize.smaller
                            color: Appearance.colors.colOnSurfaceVariant
                        }
                    }

                    Repeater {
                        id: bindRepeater
                        model: root.modeBinds

                        delegate: RowLayout {
                            id: line
                            required property var modelData
                            spacing: 16

                            function play(delay) {
                                for (let i = 0; i < keyRepeater.count; i++) {
                                    const k = keyRepeater.itemAt(i);
                                    if (k) k.tap(delay + i * 70, 240 + (keyRepeater.count - 1 - i) * 140);
                                }
                            }

                            RowLayout {
                                spacing: 4
                                Layout.minimumWidth: 120
                                Repeater {
                                    id: keyRepeater
                                    model: root.chordKeys(line.modelData)
                                    delegate: KeyboardKey {
                                        required property var modelData
                                        key: modelData
                                        pixelSize: Appearance.font.pixelSize.small
                                        interactive: true
                                    }
                                }
                            }
                            StyledText {
                                text: (line.modelData.description ?? "").replace(/^\s*Hypr mode\s*:\s*/, "")
                                font.pixelSize: Appearance.font.pixelSize.small
                                color: Appearance.colors.colOnLayer0
                            }
                        }
                    }

                    StyledText {
                        visible: root.modeBinds.length === 0
                        text: "No binds in this mode. Add them in ~/.config/hypr/custom/hypr_mode.lua"
                        font.pixelSize: Appearance.font.pixelSize.small
                        color: Appearance.colors.colOnSurfaceVariant
                    }
                }
            }
        }
    }
}
