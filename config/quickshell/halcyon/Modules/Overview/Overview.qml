import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Wayland
import Quickshell.Hyprland
import qs.Config
import qs.Components
import qs.Services

/**
 * Mission Control.
 *
 * Every workspace laid out as a card, with the windows on it drawn to
 * scale inside. Clicking a workspace goes there; clicking a window goes
 * to that window. Dragging a window onto another workspace moves it.
 *
 * Live previews come from the screencopy protocol, and they are only
 * requested while the overview is actually on screen — a live capture of
 * every window is exactly the kind of thing that quietly costs a laptop
 * an hour of battery.
 */
OverlayWindow {
    id: root

    name: "overview"
    namespaceName: "halcyon-overview"
    origin: "center"
    grabKeyboard: true

    readonly property int columns: Math.min(5, Math.max(2, Math.ceil(Math.sqrt(Workspaces.count))))
    readonly property int rows: Math.ceil(Workspaces.count / root.columns)

    /** Live previews are expensive; a still frame is usually enough. */
    readonly property bool livePreviews:
        !Theme.lowPower && !Power.onBattery && Theme.decorativeEffects

    property int highlighted: Workspaces.focusedId

    onOpened: root.highlighted = Workspaces.focusedId

    Keys.onLeftPressed: root.move(-1)
    Keys.onRightPressed: root.move(1)
    Keys.onUpPressed: root.move(-root.columns)
    Keys.onDownPressed: root.move(root.columns)
    Keys.onReturnPressed: root.go(root.highlighted)

    function move(delta: int): void {
        root.highlighted = Math.max(
            1, Math.min(Workspaces.count, root.highlighted + delta)
        );
    }

    function go(id: int): void {
        Workspaces.focus(id);
        Overlays.close(root.name);
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacingXl
        spacing: Theme.spacingLg

        Label {
            Layout.alignment: Qt.AlignHCenter
            text: "Spaces"
            variant: "titleLarge"
            tone: "secondary"
        }

        GridLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.alignment: Qt.AlignCenter
            columns: root.columns
            columnSpacing: Theme.spacingLg
            rowSpacing: Theme.spacingLg

            Repeater {
                model: Workspaces.slots

                GlassSurface {
                    id: card
                    required property var modelData

                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.maximumWidth: 420
                    Layout.maximumHeight: 260

                    level: modelData.focused ? 4 : 2
                    radius: Theme.radiusLg
                    padding: Theme.spacingSm
                    surfaceColor: modelData.focused
                        ? Theme.surfaceRaised
                        : Theme.surfaceSunken
                    borderColor: (modelData.focused || root.highlighted === modelData.id)
                        ? Theme.accent
                        : Theme.glassBorder

                    scale: root.highlighted === modelData.id ? 1.0 : 0.975
                    Behavior on scale {
                        enabled: Theme.animationsEnabled && !Theme.reducedMotion
                        NumberAnimation {
                            duration: Theme.durQuick
                            easing.type: Easing.BezierSpline
                            easing.bezierCurve: Theme.easeStandard
                        }
                    }

                    // Window previews, laid out where they actually are on
                    // the monitor so the card reads as a small screen.
                    Item {
                        id: canvas
                        anchors.fill: parent
                        clip: true

                        readonly property var monitor:
                            Workspaces.focusedMonitor ?? null
                        readonly property real scaleFactor: {
                            const width = canvas.monitor?.width ?? 1920;
                            return width > 0 ? canvas.width / width : 0.1;
                        }

                        Repeater {
                            model: Workspaces.windowsOn(card.modelData.id)

                            Item {
                                required property var modelData

                                readonly property var geometry:
                                    modelData.lastIpcObject ?? ({})

                                x: ((geometry.at ? geometry.at[0] : 0)
                                    - (canvas.monitor?.x ?? 0)) * canvas.scaleFactor
                                y: ((geometry.at ? geometry.at[1] : 0)
                                    - (canvas.monitor?.y ?? 0)) * canvas.scaleFactor
                                width: Math.max(
                                    24, (geometry.size ? geometry.size[0] : 400) * canvas.scaleFactor
                                )
                                height: Math.max(
                                    18, (geometry.size ? geometry.size[1] : 300) * canvas.scaleFactor
                                )

                                Rectangle {
                                    anchors.fill: parent
                                    radius: Theme.radiusXs
                                    color: Theme.surfaceRaised
                                    border.width: 1
                                    border.color: Theme.glassBorder
                                    clip: true

                                    ScreencopyView {
                                        anchors.fill: parent
                                        visible: root.livePreviews
                                        captureSource: modelData.wayland ?? null
                                        live: root.shown && root.livePreviews
                                        paintCursor: false
                                    }

                                    // Without a capture, show what we do
                                    // know: the application's icon.
                                    Icon {
                                        anchors.centerIn: parent
                                        visible: !root.livePreviews
                                        source: String(
                                            (modelData.lastIpcObject ?? ({})).class ?? ""
                                        ).toLowerCase()
                                        glyph: "󰖯"
                                        size: Math.min(parent.width, parent.height) * 0.4
                                        color: Theme.textTertiary
                                    }
                                }

                                StateLayer {
                                    anchors.fill: parent
                                    radius: Theme.radiusXs
                                    onClicked: {
                                        Workspaces.focusWindow(modelData.address);
                                        Overlays.close(root.name);
                                    }
                                    onRightClicked: Workspaces.closeWindow(modelData.address)
                                }
                            }
                        }
                    }

                    // Workspace label, over the previews.
                    Rectangle {
                        anchors.left: parent.left
                        anchors.bottom: parent.bottom
                        anchors.margins: Theme.spacingXs
                        width: nameLabel.implicitWidth + Theme.spacingMd
                        height: 22
                        radius: height / 2
                        color: card.modelData.focused ? Theme.accent : Theme.surfaceSolid
                        opacity: 0.92

                        Label {
                            id: nameLabel
                            anchors.centerIn: parent
                            text: card.modelData.name
                            variant: "caption"
                            font.weight: Theme.weightSemibold
                            color: card.modelData.focused ? Theme.onAccent : Theme.textSecondary
                        }
                    }

                    Label {
                        anchors.centerIn: parent
                        visible: !card.modelData.occupied
                        text: "Empty"
                        variant: "footnote"
                        tone: "tertiary"
                    }

                    StateLayer {
                        anchors.fill: parent
                        radius: card.radius
                        z: -1
                        onClicked: root.go(card.modelData.id)
                    }
                }
            }
        }

        Label {
            Layout.alignment: Qt.AlignHCenter
            text: "↑↓←→ to move · ↵ to switch · right-click a window to close it"
            variant: "caption"
            tone: "tertiary"
        }
    }
}
