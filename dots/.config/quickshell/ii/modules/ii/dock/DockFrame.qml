pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Shapes
import "../background/widgets/revolver/RevolverStyles.js" as Styles

/**
 * The dock's frame in each Halcyon theme that isn't a glass one (Dock.qml loads it in place of the plain panel):
 *
 *   hyperneo  a dark shelf with a neon hairline along the top, ember fading to violet, and a soft reflection
 *   hsr       Star Rail's gold rail: a double gold frame, a dashed track along the bottom, a star at each end
 *   red-sun   a dusk capsule, violet into night, its edge lit like the ring, a red ring at the left end
 *   icey      After ICEY's HUD: chamfered corners, a cyan edge, corner brackets, gold diamonds at the ends, and a
 *             scan of light that runs along the top
 *   ink       a manga panel: paper in a thick ink border with a hard offset shadow, and screentone at the right
 *
 * Needs only QtQuick and RevolverStyles.js.
 */
Item {
    id: frame

    property string kind: "hsr"
    property color colBase: "#14121c"
    property color colAccent: "#ffd86b"
    property color colAccent2: "#b9a4ff"
    property color colGlow: "#ff4940"

    readonly property color ink: "#141414"
    readonly property color paper: "#f7f3ea"
    readonly property real r: Math.min(height / 2, 18)

    function withAlpha(colour, alpha) {
        return Qt.rgba(colour.r, colour.g, colour.b, alpha);
    }

    // ── HyperNeo ───────────────────────────────────────────────────────────────────
    Item {
        anchors.fill: parent
        visible: frame.kind === "hyperneo"
        Rectangle {
            anchors.fill: parent
            radius: frame.r
            gradient: Gradient {
                GradientStop { position: 0.0; color: frame.withAlpha(Qt.lighter(frame.colBase, 1.6), 0.86) }
                GradientStop { position: 1.0; color: frame.withAlpha(frame.colBase, 0.92) }
            }
            border.width: 1
            border.color: frame.withAlpha("#ffffff", 0.1)
        }
        // The neon hairline.
        Rectangle {
            anchors.top: parent.top
            anchors.topMargin: 1
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width - 2 * frame.r
            height: 2
            radius: 1
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: frame.withAlpha(frame.colAccent, 0) }
                GradientStop { position: 0.3; color: frame.colAccent }
                GradientStop { position: 0.7; color: frame.colAccent2 }
                GradientStop { position: 1.0; color: frame.withAlpha(frame.colAccent2, 0) }
            }
        }
        // The reflection across the lower half.
        Rectangle {
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 4
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width - 3 * frame.r
            height: 1
            color: frame.withAlpha("#ffffff", 0.07)
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
                radius: frame.height / 2 - modelData.m
                color: "transparent"
                border.width: 2
                border.color: frame.withAlpha(frame.colGlow, modelData.a)
            }
        }
        Rectangle {
            anchors.fill: parent
            radius: frame.height / 2
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
                NumberAnimation on x {
                    running: frame.visible && frame.kind === "icey"
                    from: -80
                    to: frame.width
                    duration: 3200
                    loops: Animation.Infinite
                    easing.type: Easing.InOutSine
                }
            }
        }
    }

    // ── Manga Ink ──────────────────────────────────────────────────────────────────
    Item {
        anchors.fill: parent
        visible: frame.kind === "ink"
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
    // Screentone at the lower right: dots that grow to the right and downwards.
    readonly property string tone: {
        if (kind !== "ink" || width < 40)
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
