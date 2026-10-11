import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.Config
import qs.Services

/**
 * The revolver: a drum of installed games, drawn on the wallpaper.
 *
 * Off by default. When on, each chamber is an installed game, read from
 * the local Steam library or PrismLauncher by `halcyon revolver scan`.
 * Dragging spins the drum; releasing it leaves a chamber under the pin.
 * Nothing starts until you click the centre, so a stray drag can never
 * launch a game.
 *
 * It shows the first twelve chambers of the pool. The pool itself is
 * weighted by `widgets.revolver.mode`.
 */
Scope {
    id: root

    readonly property bool enabled: Config.get("widgets.revolver.enabled", false)
    readonly property string source: Config.get("widgets.revolver.source", "steam")
    readonly property string mode: Config.get("widgets.revolver.mode", "recent")
    readonly property int size: Math.max(200, Config.get("widgets.revolver.size", 300))
    readonly property int maxChambers: 12

    property var chambers: []
    /** Radians the drum has turned. A chamber at index i sits at spin + i·step. */
    property real spin: 0
    property int selected: -1

    readonly property real step: root.chambers.length > 0
        ? 2 * Math.PI / Math.min(root.chambers.length, root.maxChambers) : 0

    function refresh(): void {
        if (!root.enabled)
            return;
        Actions.capture(["revolver", "scan", "--source", root.source, "--mode", root.mode, "--json"],
            function (text) {
                try {
                    root.chambers = JSON.parse(text) ?? [];
                } catch (error) {
                    root.chambers = [];
                }
                root.selected = -1;
            });
    }

    /** Turn to the nearest chamber, and remember which one is under the pin. */
    function snap(): void {
        if (root.step === 0)
            return;
        const count = Math.min(root.chambers.length, root.maxChambers);
        const nearest = Math.round(-root.spin / root.step);
        const index = ((nearest % count) + count) % count;
        root.selected = index;
        snapAnimation.to = -nearest * root.step;
        snapAnimation.restart();
    }

    function fire(): void {
        if (root.selected < 0 || root.selected >= root.chambers.length)
            return;
        const chamber = root.chambers[root.selected];
        Actions.run(["revolver", "fire", chamber.source, chamber.id]);
    }

    onEnabledChanged: root.refresh()
    Component.onCompleted: root.refresh()

    NumberAnimation {
        id: snapAnimation

        target: root
        property: "spin"
        duration: Theme.durEmphasised
        easing.type: Easing.Bezier
        easing.bezierCurve: Theme.curve("emphasised")
    }

    Variants {
        model: Quickshell.screens

        LazyLoader {
            required property var modelData
            active: root.enabled

            PanelWindow {
                id: panel

                screen: modelData
                anchors { bottom: true; right: true }
                margins {
                    bottom: Theme.spacingXl
                    right: Theme.spacingXl
                }
                implicitWidth: root.size
                implicitHeight: root.size
                exclusionMode: ExclusionMode.Ignore
                color: "transparent"

                WlrLayershell.namespace: "halcyon-revolver"
                WlrLayershell.layer: WlrLayer.Background
                WlrLayershell.keyboardFocus: WlrKeyboardFocus.None

                Item {
                    id: drum

                    anchors.fill: parent

                    readonly property real centre: root.size / 2
                    readonly property real ring: root.size * 0.34
                    readonly property int count: Math.min(root.chambers.length, root.maxChambers)

                    // The drum body: a soft disc behind the chambers.
                    Rectangle {
                        anchors.centerIn: parent
                        width: drum.ring * 2 + root.size * 0.12
                        height: width
                        radius: width / 2
                        color: Qt.rgba(Theme.surface.r, Theme.surface.g, Theme.surface.b, 0.55)
                        border.width: 1
                        border.color: Theme.glassBorder
                    }

                    Repeater {
                        model: drum.count

                        Rectangle {
                            id: chamber

                            required property int index
                            readonly property var data: root.chambers[index]
                            readonly property real angle: root.spin + index * root.step - Math.PI / 2

                            width: root.size * 0.24
                            height: root.size * 0.1
                            radius: Theme.radiusSm
                            x: drum.centre + drum.ring * Math.cos(angle) - width / 2
                            y: drum.centre + drum.ring * Math.sin(angle) - height / 2
                            color: index === root.selected
                                ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.85)
                                : Qt.rgba(Theme.surfaceRaised.r, Theme.surfaceRaised.g, Theme.surfaceRaised.b, 0.8)
                            border.width: 1
                            border.color: Theme.glassBorder

                            Text {
                                anchors.fill: parent
                                anchors.leftMargin: Theme.spacingXs
                                anchors.rightMargin: Theme.spacingXs
                                text: chamber.data ? chamber.data.name : ""
                                color: chamber.index === root.selected ? Theme.onAccent : Theme.text
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.sizeCaption
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                                elide: Text.ElideRight
                                renderType: Text.QtRendering
                            }
                        }
                    }

                    // The pin at the top of the ring.
                    Rectangle {
                        x: drum.centre - width / 2
                        y: drum.centre - drum.ring - root.size * 0.12
                        width: root.size * 0.04
                        height: root.size * 0.04
                        radius: width / 2
                        color: Theme.accent
                    }

                    // The trigger: a click here starts the chamber under the pin.
                    Rectangle {
                        anchors.centerIn: parent
                        width: root.size * 0.22
                        height: width
                        radius: width / 2
                        color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.35)
                        border.width: 1
                        border.color: Theme.accent

                        Text {
                            anchors.centerIn: parent
                            text: root.selected >= 0 ? "Start" : "Spin"
                            color: Theme.text
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.sizeCaption
                            renderType: Text.QtRendering
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: root.selected >= 0 ? Qt.PointingHandCursor : Qt.ArrowCursor
                            onClicked: root.fire()
                        }
                    }

                    // Dragging around the centre turns the drum.
                    MouseArea {
                        id: drag

                        anchors.fill: parent
                        property real lastAngle: 0
                        property bool turning: false

                        function angleOf(px: real, py: real): real {
                            return Math.atan2(py - drum.centre, px - drum.centre);
                        }

                        onPressed: mouse => {
                            const radial = Math.hypot(mouse.x - drum.centre, mouse.y - drum.centre);
                            drag.turning = radial > root.size * 0.12 && radial < root.size * 0.5;
                            drag.lastAngle = drag.angleOf(mouse.x, mouse.y);
                            snapAnimation.stop();
                        }
                        onPositionChanged: mouse => {
                            if (!drag.turning)
                                return;
                            const now = drag.angleOf(mouse.x, mouse.y);
                            let delta = now - drag.lastAngle;
                            if (delta > Math.PI) delta -= 2 * Math.PI;
                            if (delta < -Math.PI) delta += 2 * Math.PI;
                            root.spin += delta;
                            drag.lastAngle = now;
                        }
                        onReleased: {
                            if (drag.turning)
                                root.snap();
                            drag.turning = false;
                        }
                        // Below the trigger, so a click on the centre is the trigger's.
                        z: -1
                    }
                }
            }
        }
    }
}
