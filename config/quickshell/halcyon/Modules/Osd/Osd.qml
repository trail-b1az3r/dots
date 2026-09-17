import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Wayland
import qs.Config
import qs.Components
import qs.Services

/**
 * The volume, brightness and media HUD.
 *
 * Appears on the focused monitor, on a timer, without taking keyboard
 * focus — pressing a volume key must never steal input from what you
 * were typing into.
 *
 * The window is destroyed between appearances rather than hidden: a HUD
 * is on screen for two seconds and absent for hours.
 */
Scope {
    id: root

    /** volume | brightness | microphone | media */
    property string kind: ""
    property bool showing: false

    readonly property int holdMs: 1800

    function show(what: string): void {
        root.kind = what;
        root.showing = true;
        hide.restart();
    }

    Timer {
        id: hide
        interval: root.holdMs
        onTriggered: root.showing = false
    }

    // Volume and brightness changes made anywhere — a keybind, the
    // Control Center, another application — raise the HUD, because the
    // user wants to see the level they just changed.
    Connections {
        target: Audio
        function onVolumeChanged(): void {
            if (Audio.ready)
                root.show("volume");
        }
        function onMutedChanged(): void {
            if (Audio.ready)
                root.show("volume");
        }
        function onInputMutedChanged(): void {
            if (Audio.ready)
                root.show("microphone");
        }
    }

    Connections {
        target: Brightness
        function onPercentChanged(): void {
            if (Brightness.available)
                root.show("brightness");
        }
    }

    LazyLoader {
        active: root.showing || fade.running

        PanelWindow {
            id: window

            screen: Workspaces.focusedMonitor
                ? Quickshell.screens.find(s => s.name === Workspaces.focusedMonitor.name) ?? null
                : null

            anchors { bottom: true }
            // Roughly an eighth of the way up a 1080p screen, which is
            // where macOS puts its HUD and where it stays clear of a
            // bottom-anchored dock.
            margins.bottom: 140
            exclusionMode: ExclusionMode.Ignore
            color: "transparent"
            // Never take focus: a HUD is feedback, not a dialog.
            focusable: false

            WlrLayershell.namespace: "halcyon-osd"
            WlrLayershell.layer: WlrLayer.Overlay
            WlrLayershell.keyboardFocus: WlrKeyboardFocus.None

            implicitWidth: 320
            implicitHeight: 92

            readonly property real level: {
                switch (root.kind) {
                case "brightness": return Brightness.percent / 100;
                case "microphone": return Audio.inputVolume;
                default: return Audio.volume;
                }
            }

            readonly property string glyph: {
                switch (root.kind) {
                case "brightness": return Brightness.glyph;
                case "microphone": return Audio.inputGlyph;
                case "media": return Media.statusGlyph;
                default: return Audio.glyph;
                }
            }

            readonly property string caption: {
                switch (root.kind) {
                case "brightness": return "Brightness";
                case "microphone": return Audio.inputMuted ? "Microphone muted" : "Microphone";
                case "media": return Media.title.length > 0 ? Media.title : "Media";
                default: return Audio.muted ? "Muted" : Audio.sinkName;
                }
            }

            GlassSurface {
                id: card
                anchors.fill: parent
                level: 3
                radius: Theme.radiusXl
                padding: Theme.panelPadding

                opacity: root.showing ? 1 : 0
                scale: root.showing ? 1 : (Theme.reducedMotion ? 1 : 0.94)

                Behavior on opacity {
                    enabled: Theme.animationsEnabled
                    NumberAnimation {
                        id: fade
                        duration: Theme.durHud
                        easing.type: Easing.BezierSpline
                        easing.bezierCurve: root.showing ? Theme.easeDecel : Theme.easeAccel
                    }
                }
                Behavior on scale {
                    enabled: Theme.animationsEnabled
                    NumberAnimation {
                        duration: Theme.durHud
                        easing.type: Easing.BezierSpline
                        easing.bezierCurve: Theme.easeEmphasis
                    }
                }

                ColumnLayout {
                    anchors.fill: parent
                    spacing: Theme.spacingSm

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingMd

                        Icon {
                            glyph: window.glyph
                            size: 22
                            color: root.kind === "microphone" && Audio.inputMuted
                                ? Theme.danger
                                : Theme.text
                        }

                        Label {
                            Layout.fillWidth: true
                            text: window.caption
                            variant: "body"
                            font.weight: Theme.weightMedium
                        }

                        Label {
                            visible: root.kind !== "media"
                            text: Math.round(window.level * 100) + "%"
                            variant: "body"
                            tone: "secondary"
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 6
                        radius: 3
                        color: Theme.surfaceSunken
                        visible: root.kind !== "media"

                        Rectangle {
                            width: Math.max(6, parent.width * Math.min(1, window.level))
                            height: parent.height
                            radius: parent.radius
                            color: {
                                if (root.kind === "microphone" && Audio.inputMuted)
                                    return Theme.danger;
                                if (root.kind === "volume" && Audio.muted)
                                    return Theme.textTertiary;
                                return Theme.accent;
                            }

                            Behavior on width {
                                enabled: Theme.animationsEnabled
                                NumberAnimation {
                                    duration: Theme.durInstant
                                    easing.type: Easing.BezierSpline
                                    easing.bezierCurve: Theme.easeDecel
                                }
                            }
                        }
                    }

                    Label {
                        Layout.fillWidth: true
                        visible: root.kind === "media" && Media.artist.length > 0
                        text: Media.artist
                        variant: "footnote"
                        tone: "secondary"
                    }
                }
            }
        }
    }
}
