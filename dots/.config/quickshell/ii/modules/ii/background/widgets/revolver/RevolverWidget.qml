import QtQuick
import Quickshell
import Quickshell.Io
import qs
import qs.services
import qs.modules.common
import qs.modules.common.functions
import qs.modules.common.widgets
import qs.modules.ii.background.widgets

/**
 * The revolver: a drum of installed games, drawn on the wallpaper.
 *
 * Off by default (background.widgets.revolver.enable). Chambers come from
 * `halcyon-theme revolver scan`, which reads the local Steam library or
 * PrismLauncher. Dragging the drum spins it; releasing leaves a chamber
 * under the pin. Nothing starts until the centre is clicked, so a stray
 * drag cannot launch a game.
 *
 * The widget does not move when dragged: the drag turns the drum. Its
 * place is set by background.widgets.revolver.x and .y.
 */
AbstractBackgroundWidget {
    id: root

    configEntryName: "revolver"
    draggable: false

    readonly property int size: Math.max(200, configEntry.size)
    readonly property int maxChambers: 12
    readonly property real centre: size / 2
    readonly property real ring: size * 0.34

    property var chambers: []
    /** Radians the drum has turned. The chamber at index i sits at spin + i·step. */
    property real spin: 0
    property int selected: -1

    readonly property int count: Math.min(chambers.length, maxChambers)
    readonly property real step: count > 0 ? 2 * Math.PI / count : 0

    implicitWidth: size
    implicitHeight: size

    function refresh(): void {
        scanner.running = true;
    }

    /** Turn to the nearest chamber, and remember which one is under the pin. */
    function snap(): void {
        if (step === 0)
            return;
        const nearest = Math.round(-spin / step);
        selected = ((nearest % count) + count) % count;
        snapAnimation.to = -nearest * step;
        snapAnimation.restart();
    }

    function fire(): void {
        if (selected < 0 || selected >= chambers.length)
            return;
        const chamber = chambers[selected];
        // The source and id are passed as arguments, never spliced into the script.
        Quickshell.execDetached(["bash", "-c",
            'exec "$HOME/.config/hypr/hyprland/halcyon/halcyon-theme" revolver fire "$1" "$2"',
            "bash", chamber.source, chamber.id]);
    }

    onVisibleChanged: if (visible) refresh()
    Component.onCompleted: refresh()

    Process {
        id: scanner

        command: ["bash", "-c",
            'exec "$HOME/.config/hypr/hyprland/halcyon/halcyon-theme" revolver scan --json' +
            ' --source "$1" --mode "$2"',
            "bash", configEntry.source, configEntry.mode]
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    root.chambers = JSON.parse(this.text) ?? [];
                } catch (error) {
                    root.chambers = [];
                }
                root.selected = -1;
            }
        }
    }

    NumberAnimation {
        id: snapAnimation

        target: root
        property: "spin"
        duration: Appearance.animation.elementMove.duration
        easing.type: Appearance.animation.elementMove.type
        easing.bezierCurve: Appearance.animation.elementMove.bezierCurve
    }

    // The drum body: a soft disc behind the chambers.
    Rectangle {
        anchors.centerIn: parent
        width: root.ring * 2 + root.size * 0.12
        height: width
        radius: width / 2
        color: ColorUtils.transparentize(Appearance.colors.colLayer0, 0.35)
        border.width: 1
        border.color: Appearance.colors.colLayer0Border
    }

    Repeater {
        model: root.count

        Rectangle {
            id: chamber

            required property int index
            readonly property var entry: root.chambers[index]
            readonly property real angle: root.spin + index * root.step - Math.PI / 2

            width: root.size * 0.24
            height: root.size * 0.1
            radius: Appearance.rounding.small
            x: root.centre + root.ring * Math.cos(angle) - width / 2
            y: root.centre + root.ring * Math.sin(angle) - height / 2
            color: index === root.selected
                ? ColorUtils.transparentize(Appearance.colors.colPrimary, 0.1)
                : Appearance.colors.colLayer2
            border.width: 1
            border.color: Appearance.colors.colLayer0Border

            StyledText {
                anchors.fill: parent
                anchors.leftMargin: 4
                anchors.rightMargin: 4
                text: chamber.entry ? chamber.entry.name : ""
                color: chamber.index === root.selected ? Appearance.colors.colOnPrimary : Appearance.colors.colOnLayer2
                font.family: Appearance.font.family.main
                font.pixelSize: 12
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
        }
    }

    // The pin at the top of the ring.
    Rectangle {
        x: root.centre - width / 2
        y: root.centre - root.ring - root.size * 0.12
        width: root.size * 0.04
        height: width
        radius: width / 2
        color: Appearance.colors.colPrimary
    }

    // The trigger: a click here starts the chamber under the pin.
    Rectangle {
        anchors.centerIn: parent
        width: root.size * 0.22
        height: width
        radius: width / 2
        color: ColorUtils.transparentize(Appearance.colors.colPrimary, 0.6)
        border.width: 1
        border.color: Appearance.colors.colPrimary

        StyledText {
            anchors.centerIn: parent
            text: root.selected >= 0 ? Translation.tr("Start") : Translation.tr("Spin")
            color: Appearance.colors.colOnLayer0
            font.family: Appearance.font.family.main
            font.pixelSize: 12
        }

        MouseArea {
            anchors.fill: parent
            cursorShape: root.selected >= 0 ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: root.fire()
        }
    }

    // Dragging around the centre turns the drum. Below the trigger, so a
    // click on the centre is the trigger's.
    MouseArea {
        id: drag

        anchors.fill: parent
        z: -1
        property real lastAngle: 0
        property bool turning: false

        function angleOf(px: real, py: real): real {
            return Math.atan2(py - root.centre, px - root.centre);
        }

        onPressed: mouse => {
            const radial = Math.hypot(mouse.x - root.centre, mouse.y - root.centre);
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
    }
}
