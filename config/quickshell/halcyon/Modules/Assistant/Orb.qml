import QtQuick
import QtQuick.Effects
import qs.Config
import qs.Services

/**
 * The assistant's orb.
 *
 * A soft core with a blurred halo and three rings that breathe. The halo
 * is a heavily blurred copy of the core rather than a radial-gradient
 * asset: MultiEffect does it on the GPU, it follows the accent colour
 * automatically, and there is no image to ship or scale.
 *
 * The animation is driven by state, not by a clock: idle breathes
 * slowly, listening pulses with the input level, thinking rotates,
 * speaking ripples outward. With reduced motion on, the orb changes
 * colour and stops moving — the state is still legible, and nothing
 * oscillates.
 */
Item {
    id: root

    property int size: 128
    property real level: Assistant.level
    property string state: Assistant.state

    implicitWidth: root.size
    implicitHeight: root.size

    readonly property color tint: {
        switch (root.state) {
        case "listening": return Theme.accent;
        case "thinking": return Theme.secondary;
        case "speaking": return Theme.tertiary;
        case "offline": return Theme.textTertiary;
        default: return Theme.accent;
        }
    }

    readonly property bool animate: Theme.animationsEnabled && !Theme.reducedMotion

    Behavior on tint {
        enabled: Theme.animationsEnabled
        ColorAnimation {
            duration: Theme.durStandard
            easing.type: Easing.BezierSpline
            easing.bezierCurve: Theme.easeStandard
        }
    }

    // ── Halo ───────────────────────────────────────────────────────────

    Item {
        id: haloSource
        anchors.centerIn: parent
        width: root.size * 0.78
        height: width
        visible: false
        layer.enabled: true

        Rectangle {
            anchors.fill: parent
            radius: width / 2
            color: root.tint
        }
    }

    MultiEffect {
        anchors.centerIn: parent
        width: haloSource.width
        height: haloSource.height
        source: haloSource
        autoPaddingEnabled: true
        blurEnabled: Theme.decorativeEffects
        blur: 1.0
        blurMax: 48
        opacity: {
            if (root.state === "offline") return 0.18;
            if (root.state === "listening") return 0.34 + root.level * 0.32;
            if (root.state === "speaking") return 0.46;
            return 0.30;
        }
        scale: root.state === "listening" ? 1.0 + root.level * 0.22 : 1.0

        Behavior on opacity {
            enabled: Theme.animationsEnabled
            NumberAnimation { duration: Theme.durQuick }
        }
        Behavior on scale {
            enabled: root.animate
            NumberAnimation {
                duration: 110
                easing.type: Easing.BezierSpline
                easing.bezierCurve: Theme.easeDecel
            }
        }
    }

    // ── Rings ──────────────────────────────────────────────────────────

    Repeater {
        model: Theme.decorativeEffects ? 3 : 0

        Rectangle {
            required property int index

            anchors.centerIn: parent
            width: root.size * (0.66 + index * 0.13)
            height: width
            radius: width / 2
            color: "transparent"
            border.width: 1
            border.color: Qt.rgba(root.tint.r, root.tint.g, root.tint.b,
                                  0.30 - index * 0.08)

            // Rings expand outward while speaking, the way a sound would.
            SequentialAnimation on scale {
                running: root.animate && root.state === "speaking"
                loops: Animation.Infinite
                PauseAnimation { duration: index * 220 }
                NumberAnimation {
                    from: 0.92
                    to: 1.18
                    duration: 1500
                    easing.type: Easing.BezierSpline
                    easing.bezierCurve: Theme.easeDecel
                }
                NumberAnimation { to: 0.92; duration: 0 }
            }

            // And breathe gently when idle, so the orb never looks dead.
            SequentialAnimation on opacity {
                running: root.animate && (root.state === "idle" || root.state === "thinking")
                loops: Animation.Infinite
                PauseAnimation { duration: index * 300 }
                NumberAnimation { to: 0.35; duration: 2000; easing.type: Easing.InOutSine }
                NumberAnimation { to: 1.0; duration: 2000; easing.type: Easing.InOutSine }
            }
        }
    }

    // ── Core ───────────────────────────────────────────────────────────

    Rectangle {
        id: core
        anchors.centerIn: parent
        width: root.size * 0.5
        height: width
        radius: width / 2

        gradient: Gradient {
            GradientStop {
                position: 0.0
                color: Qt.lighter(root.tint, Theme.isDark ? 1.35 : 1.12)
            }
            GradientStop { position: 1.0; color: root.tint }
        }

        scale: {
            if (root.state === "listening")
                return 1.0 + root.level * 0.16;
            return 1.0;
        }

        Behavior on scale {
            enabled: root.animate
            NumberAnimation {
                duration: 110
                easing.type: Easing.BezierSpline
                easing.bezierCurve: Theme.easeDecel
            }
        }

        // A specular dot, offset up and left: the single cue that turns a
        // flat disc into a sphere.
        Rectangle {
            visible: Theme.decorativeEffects
            width: parent.width * 0.3
            height: width
            radius: width / 2
            x: parent.width * 0.18
            y: parent.height * 0.14
            opacity: 0.4
            gradient: Gradient {
                GradientStop { position: 0.0; color: Qt.rgba(1, 1, 1, 0.8) }
                GradientStop { position: 1.0; color: "transparent" }
            }
        }

        // Thinking is a slow rotation of the highlight rather than a
        // spinner: it reads as "working" without a progress metaphor
        // there is no progress to report.
        RotationAnimation on rotation {
            running: root.animate && root.state === "thinking"
            loops: Animation.Infinite
            from: 0
            to: 360
            duration: 3200
        }
    }

    // ── Waveform ───────────────────────────────────────────────────────
    //
    // Only while listening. Bars are driven by the level with a per-bar
    // phase offset, so it moves like sound rather than like a bar chart.

    Row {
        anchors.centerIn: parent
        spacing: 3
        visible: root.state === "listening" && Theme.decorativeEffects

        Repeater {
            model: 5

            Rectangle {
                required property int index

                width: 3
                radius: 1.5
                color: Theme.onAccent
                opacity: 0.85
                anchors.verticalCenter: parent.verticalCenter

                readonly property real weight: 1.0 - Math.abs(index - 2) * 0.22
                height: root.animate
                    ? Math.max(4, root.size * 0.05 + root.level * root.size * 0.24 * weight)
                    : root.size * 0.1

                Behavior on height {
                    enabled: root.animate
                    NumberAnimation {
                        duration: 90 + index * 18
                        easing.type: Easing.BezierSpline
                        easing.bezierCurve: Theme.easeDecel
                    }
                }
            }
        }
    }

    Accessible.role: Accessible.Indicator
    Accessible.name: "Assistant"
    Accessible.description: Assistant.statusText
}
