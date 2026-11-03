pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Shapes
import "../background/widgets/revolver/RevolverStyles.js" as Styles

/**
 * The dock's frame in each Halcyon theme that isn't a glass one (Dock.qml loads it in place of the plain panel):
 *
 *   hyperneo  smoked glass in a neon edge (ember, rose, violet), a lit lip on top and an ember glow along the bottom
 *   hsr       Star Rail's gold rail: a double gold frame, a dashed track along the bottom, a star at each end
 *   red-sun   a dusk capsule, violet into night, its edge lit like the ring, a red ring at the left end
 *   icey      After ICEY's HUD: chamfered corners, a cyan edge, corner brackets, gold diamonds at the ends, and a
 *             scan of light that runs along the top
 *   ink       a manga panel: paper in a thick ink border with a hard offset shadow, and screentone at the right
 *             (inverted: an ink panel with paper lines, for the top bar, whose text is light)
 *   ink-dark  Manga Ink Dark: the ink panel with paper lines everywhere
 *   sao       Sword Art Online's HUD: slate glass with a fine light edge, an orange rule along the top, and a white
 *             notch at each end, like the game's bars
 *   silence   black, almost nothing: a faint edge, a red hairline that is brightest in the middle, and at the right
 *             end two small red eyes that slowly open and close
 *
 * The dock and the top bar both use it, so they match.
 * Needs only QtQuick and RevolverStyles.js.
 */
Item {
    id: frame

    property string kind: "hsr"
    property color colBase: "#14121c"
    property color colAccent: "#ffd86b"
    property color colAccent2: "#b9a4ff"
    property color colGlow: "#ff4940"
    /** Manga Ink in negative: an ink panel with paper lines, for places whose text is light (the top bar). */
    property bool inverted: false

    readonly property bool negative: inverted || kind === "ink-dark"
    readonly property color ink: negative ? "#f1ece2" : "#141414"
    readonly property color paper: negative ? "#0d0d0e" : "#f7f3ea"
    readonly property real r: Math.min(height / 2, 18)
    // Red Sun's capsule: round ends on a bar, rounded corners on a tall panel.
    readonly property real capsule: Math.min(height / 2, 30)

    function withAlpha(colour, alpha) {
        return Qt.rgba(colour.r, colour.g, colour.b, alpha);
    }

    // ── HyperNeo ───────────────────────────────────────────────────────────────────
    // Smoked glass in a neon edge that runs ember, rose, violet; a lit lip along the top and an ember glow
    // reflected along the bottom, brightest in the middle. Plain rectangles and gradients: no shaders, no layers.
    Item {
        anchors.fill: parent
        visible: frame.kind === "hyperneo"
        // The neon edge: a gradient slab with the glass laid 1.5 px inside it.
        Rectangle {
            anchors.fill: parent
            radius: frame.r
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: frame.withAlpha(frame.colAccent, 0.95) }
                GradientStop { position: 0.5; color: frame.withAlpha(frame.colAccent2, 0.95) }
                GradientStop { position: 1.0; color: frame.withAlpha("#9b7bff", 0.95) }
            }
        }
        Rectangle {
            anchors.fill: parent
            anchors.margins: 1.5
            radius: frame.r - 1.5
            gradient: Gradient {
                GradientStop { position: 0.0; color: frame.withAlpha("#2a1c1e", 0.94) }
                GradientStop { position: 0.55; color: frame.withAlpha("#160f11", 0.95) }
                GradientStop { position: 1.0; color: frame.withAlpha("#0c0809", 0.96) }
            }
        }
        // The lit lip.
        Rectangle {
            anchors.top: parent.top
            anchors.topMargin: 2.5
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width - 2 * frame.r
            height: 1
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: frame.withAlpha("#ffffff", 0) }
                GradientStop { position: 0.5; color: frame.withAlpha("#ffffff", 0.22) }
                GradientStop { position: 1.0; color: frame.withAlpha("#ffffff", 0) }
            }
        }
        // The glow along the bottom: a bright line, brightest in the middle, with a soft halo above it.
        Rectangle {
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 2
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width * 0.7
            height: 6
            radius: 3
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: frame.withAlpha(frame.colAccent, 0) }
                GradientStop { position: 0.5; color: frame.withAlpha(frame.colAccent, 0.22) }
                GradientStop { position: 1.0; color: frame.withAlpha(frame.colAccent2, 0) }
            }
        }
        Rectangle {
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 2
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width * 0.62
            height: 1.5
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: frame.withAlpha(frame.colAccent, 0) }
                GradientStop { position: 0.5; color: Qt.lighter(frame.colAccent, 1.25) }
                GradientStop { position: 1.0; color: frame.withAlpha(frame.colAccent2, 0) }
            }
        }
    }

    // ── Sword Art Online ───────────────────────────────────────────────────────────
    Item {
        anchors.fill: parent
        visible: frame.kind === "sao"
        Rectangle {
            anchors.fill: parent
            radius: Math.min(6, frame.height / 2)
            gradient: Gradient {
                GradientStop { position: 0.0; color: frame.withAlpha("#28313C", 0.9) }
                GradientStop { position: 1.0; color: frame.withAlpha("#161B22", 0.92) }
            }
            border.width: 1
            border.color: frame.withAlpha("#FFFFFF", 0.14)
        }
        // The orange rule, brightest in the middle.
        Rectangle {
            anchors.top: parent.top
            anchors.topMargin: 1
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width * 0.5
            height: 2
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: frame.withAlpha("#F5A43B", 0) }
                GradientStop { position: 0.5; color: "#F5A43B" }
                GradientStop { position: 1.0; color: frame.withAlpha("#F5A43B", 0) }
            }
        }
        // The notches.
        Repeater {
            model: 2
            Rectangle {
                required property int index
                width: 7
                height: 7
                rotation: 45
                x: index === 0 ? 6 : frame.width - 13
                anchors.verticalCenter: parent.verticalCenter
                color: frame.withAlpha("#F4F6F8", 0.85)
                visible: frame.width > 60
            }
        }
    }

    // ── Star Rail ──────────────────────────────────────────────────────────────────
    Item {
        anchors.fill: parent
        visible: frame.kind === "hsr"
        Rectangle {
            anchors.fill: parent
            radius: 10
            color: frame.withAlpha(frame.colBase, 0.92)
            border.width: 2
            border.color: frame.colAccent
        }
        Rectangle {
            anchors.fill: parent
            anchors.margins: 5
            radius: 6
            color: "transparent"
            border.width: 1
            border.color: frame.withAlpha(frame.colAccent, 0.5)
        }
        Shape {
            anchors.fill: parent
            // The rail's track along the bottom.
            ShapePath {
                strokeWidth: 2
                strokeColor: frame.withAlpha(frame.colAccent, 0.45)
                strokeStyle: ShapePath.DashLine
                dashPattern: [1.2, 2.4]
                fillColor: "transparent"
                startX: 22; startY: frame.height - 9
                PathLine { x: frame.width - 22; y: frame.height - 9 }
            }
            // A four-point star at each end, over the frame.
            ShapePath {
                strokeWidth: -1
                fillColor: frame.colAccent
                PathSvg { path: Styles.sparkle(0, frame.height / 2, 9) + " " + Styles.sparkle(frame.width, frame.height / 2, 9) }
            }
        }
    }

    // ── Red Sun ────────────────────────────────────────────────────────────────────
    Item {
        anchors.fill: parent
        visible: frame.kind === "red-sun"
        // The ring's light round the capsule.
        Repeater {
            model: [{ m: -6, a: 0.06 }, { m: -3, a: 0.14 }, { m: -1, a: 0.32 }]
            Rectangle {
                required property var modelData
                anchors.fill: parent
                anchors.margins: modelData.m
                radius: frame.capsule - modelData.m
                color: "transparent"
                border.width: 2
                border.color: frame.withAlpha(frame.colGlow, modelData.a)
            }
        }
        Rectangle {
            anchors.fill: parent
            radius: frame.capsule
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#3a1a33" }
                GradientStop { position: 1.0; color: "#0d0710" }
            }
            border.width: 1.5
            border.color: frame.colGlow
        }
        // The horizon, and the sun's ring at the left end.
        Rectangle {
            anchors.bottom: parent.bottom
            anchors.bottomMargin: frame.height * 0.3
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width - frame.height
            height: 1
            color: frame.withAlpha(frame.colGlow, 0.25)
        }
        Rectangle {
            x: -7
            anchors.verticalCenter: parent.verticalCenter
            width: 16
            height: 16
            radius: 8
            color: "#0d0710"
            border.width: 2.5
            border.color: frame.colGlow
        }
    }

    // ── After ICEY ─────────────────────────────────────────────────────────────────
    Item {
        anchors.fill: parent
        visible: frame.kind === "icey"
        Shape {
            anchors.fill: parent
            ShapePath {
                strokeWidth: 1.5
                strokeColor: frame.withAlpha(frame.colAccent, 0.9)
                fillColor: frame.withAlpha(frame.colBase, 0.94)
                joinStyle: ShapePath.MiterJoin
                PathSvg { path: Styles.chamferRect(1, 1, frame.width - 2, frame.height - 2, 12) }
            }
            // Brackets just outside the corners.
            ShapePath {
                strokeWidth: 2
                strokeColor: frame.colAccent
                fillColor: "transparent"
                joinStyle: ShapePath.MiterJoin
                PathSvg {
                    path: "M -5 10 L -5 -5 L 10 -5 M " + (frame.width - 10) + " -5 L " + (frame.width + 5) + " -5 L " + (frame.width + 5) + " 10"
                        + " M -5 " + (frame.height - 10) + " L -5 " + (frame.height + 5) + " L 10 " + (frame.height + 5)
                        + " M " + (frame.width - 10) + " " + (frame.height + 5) + " L " + (frame.width + 5) + " " + (frame.height + 5) + " L " + (frame.width + 5) + " " + (frame.height - 10)
                }
            }
            ShapePath {
                strokeWidth: -1
                fillColor: frame.colAccent2
                PathSvg { path: Styles.diamond(-1, frame.height / 2, 4) + " " + Styles.diamond(frame.width + 1, frame.height / 2, 4) }
            }
        }
        // The scan of light along the top edge.
        Item {
            anchors.fill: parent
            clip: true
            Rectangle {
                id: scan
                y: 1
                width: 80
                height: 2
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: frame.withAlpha(frame.colAccent, 0) }
                    GradientStop { position: 0.5; color: Qt.lighter(frame.colAccent, 1.4) }
                    GradientStop { position: 1.0; color: frame.withAlpha(frame.colAccent, 0) }
                }
                x: -80
                // One sweep, then a long rest with nothing moving, so the bar and the dock are not redrawn every
                // frame for it.
                SequentialAnimation on x {
                    running: frame.visible && frame.kind === "icey"
                    loops: Animation.Infinite
                    NumberAnimation { from: -80; to: frame.width; duration: 3200; easing.type: Easing.InOutSine }
                    PauseAnimation { duration: 9000 }
                }
            }
        }
    }

    // ── Manga Ink ──────────────────────────────────────────────────────────────────
    Item {
        anchors.fill: parent
        visible: frame.kind === "ink" || frame.kind === "ink-dark"
        // A manga panel's hard shadow, straight down and right.
        Rectangle {
            x: 5
            y: 5
            width: parent.width
            height: parent.height
            radius: 6
            color: frame.ink
        }
        Rectangle {
            anchors.fill: parent
            radius: 6
            color: frame.paper
            border.width: 3
            border.color: frame.ink
        }
        Shape {
            anchors.fill: parent
            anchors.margins: 4
            clip: true
            ShapePath {
                strokeWidth: -1
                // Light, so the buttons over it still read.
                fillColor: frame.withAlpha(frame.ink, 0.32)
                PathSvg { path: frame.tone }
            }
        }
    }
    // ── Silence ────────────────────────────────────────────────────────────────────
    Item {
        anchors.fill: parent
        visible: frame.kind === "silence"
        Rectangle {
            anchors.fill: parent
            radius: frame.r
            color: frame.withAlpha("#000000", 0.9)
            border.width: 1
            border.color: frame.withAlpha("#ffffff", 0.06)
        }
        // The red hairline, brightest in the middle.
        Rectangle {
            anchors.bottom: parent.bottom
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width - 2 * frame.r
            height: 1
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: frame.withAlpha(frame.colAccent, 0) }
                GradientStop { position: 0.5; color: frame.withAlpha(frame.colAccent, 0.85) }
                GradientStop { position: 1.0; color: frame.withAlpha(frame.colAccent, 0) }
            }
        }
        // Two red eyes at the right end, opening and closing slowly.
        Row {
            id: eyes
            anchors.right: parent.right
            anchors.rightMargin: Math.max(6, frame.r * 0.55)
            anchors.verticalCenter: parent.verticalCenter
            spacing: 5
            opacity: 0.4
            Repeater {
                model: 2
                Item {
                    width: 6
                    height: 6
                    Rectangle {
                        anchors.centerIn: parent
                        width: 10
                        height: 10
                        radius: 5
                        color: frame.withAlpha(frame.colAccent, 0.22)
                    }
                    Rectangle {
                        anchors.centerIn: parent
                        width: 5
                        height: 3
                        radius: 1.5
                        color: Qt.lighter(frame.colAccent, 1.15)
                    }
                }
            }
            SequentialAnimation on opacity {
                running: frame.visible && frame.kind === "silence"
                loops: Animation.Infinite
                NumberAnimation { to: 1; duration: 2600; easing.type: Easing.InOutSine }
                PauseAnimation { duration: 7000 }
                NumberAnimation { to: 0.35; duration: 2600; easing.type: Easing.InOutSine }
                PauseAnimation { duration: 5000 }
            }
        }
    }

    // Screentone at the lower right: dots that grow to the right and downwards.
    readonly property string tone: {
        if ((kind !== "ink" && kind !== "ink-dark") || width < 40)
            return "";
        let d = "";
        const step = 6, w = width - 8, h = height - 8;
        for (let y = step / 2; y < h; y += step) {
            const row = Math.round(y / step);
            for (let x = w * 0.62 + (row % 2) * step / 2; x < w; x += step) {
                // Growing to the right and towards the bottom edge, clear of the middle of the buttons.
                const dot = Math.min(1, (x - w * 0.62) / (w * 0.38)) * Math.min(1, Math.max(0, (y / h - 0.35) / 0.65)) * step * 0.34;
                if (dot < 0.4)
                    continue;
                d += `M ${x - dot} ${y} A ${dot} ${dot} 0 1 0 ${x + dot} ${y} A ${dot} ${dot} 0 1 0 ${x - dot} ${y} `;
            }
        }
        return d;
    }
}
