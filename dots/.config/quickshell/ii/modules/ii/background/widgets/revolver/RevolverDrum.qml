pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Shapes
import "RevolverStyles.js" as Styles

/**
 * The revolver's drum, drawn in the active theme's style (RevolverStyles.js):
 *
 *   default   a Material cookie dial with round chambers
 *   red-sun   the red ring itself: lit only while it turns, with ember beads riding on it
 *   glass     a faceted glass disc with cut-gem chambers
 *   hyperneo  a squircle with squircle chambers, like app icons
 *   hsr       a gold rail with four-pointed star chambers
 *
 * Only the look lives here. RevolverWidget turns the rotor, picks the live chamber and fires, and passes the
 * colours in, so this file needs nothing but QtQuick and can be drawn on its own.
 */
Item {
    id: drum

    property var style: Styles.styleFor("")
    property color colBase: "#3a2c3c"
    property color colOn: "#f3e6e4"
    property color colAccent: "#ff8a7a"
    property color colChamber: "#16111c"
    property color colGlow: "#ff4940"
    property color colHot: "#ffe2d6"
    property string fontFamily: ""

    property var chambers: []
    property int chamberCount: 8
    property int liveIndex: -1
    property int ejectingIndex: -1
    property bool spinning: false
    /** 0..1: how fast the drum turns. Drives the trails and, in Red Sun, how hot the ring is. */
    property real spinSpeed: 0
    property int spinDirection: 1
    /** 0..1: the Red Sun ring's light. RevolverWidget raises it while the drum turns. */
    property real heat: 0
    /** Red Sun away from the painted ring (another wallpaper, or followRing off): the drum draws the whole sun
     *  itself, lit at rest, instead of leaving the ring to the wallpaper. */
    property bool standalone: false
    /** How brightly the ring burns: on the painted ring only while it turns; standalone, always. */
    readonly property real ringLight: standalone ? Math.max(0.8, heat) : heat
    property bool locked: false
    readonly property alias rotor: rotor

    /** Halfway through an eject, while the chamber is out of sight: load the next round now. */
    signal swapChamber(int index)
    /** The reloaded chamber has settled. */
    signal ejectDone(int index)

    readonly property real c: Styles.CENTRE
    readonly property bool redSun: style.id === "red-sun"

    width: 230
    height: 230

    function platePath(cx, cy, r) {
        switch (drum.style.drum) {
        case "cookie": return Styles.cookie(cx, cy, r * 0.95, drum.style.waves, 0.04);
        case "squircle": return Styles.squircle(cx, cy, r * 0.96, 4.6);
        case "rail": return Styles.circle(cx, cy, r * 0.97);
        case "facets": return Styles.polygon(cx, cy, r, 8, 22.5);
        default: return Styles.circle(cx, cy, r);
        }
    }

    function withAlpha(colour, alpha) {
        return Qt.rgba(colour.r, colour.g, colour.b, alpha);
    }

    // Drawn on a surface a little larger than the stage, so the hammer and the glows are not cut off, in one
    // multisampled layer that smooths every outline, on any Qt 6.
    readonly property real pad: 34
    Item {
        id: surface
        x: -drum.pad
        y: -drum.pad
        width: drum.width + 2 * drum.pad
        height: drum.height + 2 * drum.pad
        layer.enabled: true
        layer.samples: 4
        layer.smooth: true

        Item {
            id: stage
            x: drum.pad
            y: drum.pad
            width: drum.width
            height: drum.height

            // ── The plate behind everything ──────────────────────────────────────

            // A soft shadow under solid plates.
            Shape {
                anchors.fill: parent
                visible: !drum.redSun && drum.style.drum !== "facets"
                opacity: 0.32
                y: 5
                ShapePath {
                    strokeWidth: -1
                    fillColor: "#000000"
                    PathSvg { path: drum.platePath(drum.c, drum.c + 1, 112) }
                }
            }


            // Solid plates: cookie, squircle, rail.
            Shape {
                id: plate
                anchors.fill: parent
                visible: drum.style.drum === "cookie" || drum.style.drum === "squircle" || drum.style.drum === "rail"
                ShapePath {
                    strokeWidth: 1.2
                    strokeColor: drum.withAlpha(drum.colOn, drum.style.drum === "rail" ? 0.0 : 0.14)
                    fillGradient: RadialGradient {
                        centerX: drum.c; centerY: drum.c - 30
                        centerRadius: 150
                        focalX: drum.c; focalY: drum.c - 40
                        GradientStop { position: 0.0; color: Qt.lighter(drum.colBase, drum.style.drum === "rail" ? 1.35 : 1.18) }
                        GradientStop { position: 1.0; color: Qt.darker(drum.colBase, 1.25) }
                    }
                    PathSvg { path: drum.platePath(drum.c, drum.c, 112) }
                }
                // A highlight along the top edge, as on a lit, slightly domed surface.
                ShapePath {
                    strokeWidth: 2
                    strokeColor: drum.withAlpha("#ffffff", 0.16)
                    fillColor: "transparent"
                    capStyle: ShapePath.RoundCap
                    PathSvg { path: Styles.arc(drum.c, drum.c, drum.style.drum === "squircle" ? 104 : 101, -160, -20) }
                }
                // A groove just inside the edge.
                ShapePath {
                    strokeWidth: 1
                    strokeColor: drum.withAlpha("#000000", 0.22)
                    fillColor: "transparent"
                    PathSvg { path: drum.platePath(drum.c, drum.c, 98) }
                }
            }

            // Star Rail: a gold rail of two rings with the track between them.
            Shape {
                anchors.fill: parent
                visible: drum.style.drum === "rail"
                ShapePath {
                    strokeWidth: 2.2
                    strokeColor: drum.colAccent
                    fillColor: "transparent"
                    PathSvg { path: Styles.circle(drum.c, drum.c, 106) }
                }
                ShapePath {
                    strokeWidth: 1
                    strokeColor: drum.withAlpha(drum.colAccent, 0.6)
                    fillColor: "transparent"
                    PathSvg { path: Styles.circle(drum.c, drum.c, 54) }
                }
            }

            // Glass: a disc cut into facets, each catching a different amount of light.
            Shape {
                anchors.fill: parent
                visible: drum.style.drum === "facets"
                Instantiator {
                    model: 8
                    delegate: ShapePath {
                        required property int index
                        strokeWidth: 1
                        strokeColor: drum.withAlpha("#ffffff", 0.32)
                        fillColor: drum.withAlpha(index % 2 === 0 ? "#ffffff" : drum.colAccent, [0.13, 0.05, 0.10, 0.03, 0.08, 0.04, 0.12, 0.06][index])
                        PathSvg { path: Styles.facet(drum.c, drum.c, 112, 8, index, 22.5) }
                    }
                    onObjectAdded: (index, object) => glassFacets.data.push(object)
                }
                id: glassFacets
                ShapePath {
                    strokeWidth: 1.6
                    strokeColor: drum.withAlpha("#ffffff", 0.55)
                    fillColor: "transparent"
                    PathSvg { path: Styles.polygon(drum.c, drum.c, 112, 8, 22.5) }
                }
            }

            // Red Sun on its own: the sun's disc inside the ring, dark in the middle and glowing towards the rim,
            // like the painted one.
            Shape {
                anchors.fill: parent
                visible: drum.redSun && drum.standalone
                ShapePath {
                    strokeWidth: -1
                    fillGradient: RadialGradient {
                        centerX: drum.c; centerY: drum.c
                        centerRadius: 88
                        focalX: drum.c; focalY: drum.c - 10
                        GradientStop { position: 0.0; color: drum.withAlpha("#1a0610", 0.92) }
                        GradientStop { position: 0.55; color: drum.withAlpha("#4a0c16", 0.86) }
                        GradientStop { position: 0.78; color: drum.withAlpha("#8a1a22", 0.7) }
                        GradientStop { position: 0.9; color: drum.withAlpha(drum.colGlow, 0.55) }
                        GradientStop { position: 1.0; color: drum.withAlpha(drum.colGlow, 0.2) }
                    }
                    PathSvg { path: Styles.circle(drum.c, drum.c, 88) }
                }
            }

            // Red Sun: a red haze where the ring burns.
            Shape {
                anchors.fill: parent
                visible: drum.redSun
                opacity: 0.35 + 0.65 * drum.ringLight
                ShapePath {
                    strokeWidth: -1
                    fillGradient: RadialGradient {
                        centerX: drum.c; centerY: drum.c
                        centerRadius: 128
                        focalX: drum.c; focalY: drum.c
                        GradientStop { position: 0.0; color: drum.withAlpha(drum.colGlow, 0.0) }
                        GradientStop { position: 0.55; color: drum.withAlpha(drum.colGlow, 0.10) }
                        GradientStop { position: 0.72; color: drum.withAlpha(drum.colGlow, 0.32) }
                        GradientStop { position: 0.85; color: drum.withAlpha(drum.colGlow, 0.12) }
                        GradientStop { position: 1.0; color: drum.withAlpha(drum.colGlow, 0.0) }
                    }
                    PathSvg { path: Styles.circle(drum.c, drum.c, 128) }
                }
            }

            // ── The rotor: everything that turns ─────────────────────────────────

            Item {
                id: rotor
                anchors.fill: parent
                rotation: 0

                // Dial ticks on the solid plates.
                Shape {
                    anchors.fill: parent
                    visible: drum.style.drum === "cookie" || drum.style.drum === "squircle"
                    ShapePath {
                        strokeWidth: 1.4
                        strokeColor: drum.withAlpha(drum.colOn, 0.22)
                        capStyle: ShapePath.RoundCap
                        fillColor: "transparent"
                        PathSvg { path: Styles.ticks(drum.c, drum.c, 104, 108, 32, 0) }
                    }
                }

                // Star Rail: the dashed track, which runs as the drum turns.
                Shape {
                    anchors.fill: parent
                    visible: drum.style.drum === "rail"
                    ShapePath {
                        strokeWidth: 3
                        strokeColor: drum.withAlpha(drum.colAccent, 0.45)
                        strokeStyle: ShapePath.DashLine
                        dashPattern: [1.2, 2.4]
                        fillColor: "transparent"
                        PathSvg { path: Styles.circle(drum.c, drum.c, 101) }
                    }
                }

                // Red Sun: the ring, lit while it turns. Broken like the painted one.
                Shape {
                    id: sunRing
                    anchors.fill: parent
                    visible: drum.redSun
                    opacity: drum.ringLight
                    Instantiator {
                        // Glow from wide and faint to the white-hot core, for each lit arc.
                        model: [
                            { w: 46, a: 0.06, hot: false }, { w: 32, a: 0.14, hot: false }, { w: 22, a: 0.34, hot: false },
                            { w: 16, a: 0.95, hot: false }, { w: 10, a: 1.0, hot: true }
                        ]
                        delegate: ShapePath {
                            required property var modelData
                            strokeWidth: modelData.w
                            strokeColor: modelData.hot ? drum.colHot : drum.withAlpha(drum.colGlow, modelData.a)
                            capStyle: ShapePath.RoundCap
                            fillColor: "transparent"
                            PathSvg { path: Styles.arc(drum.c, drum.c, 92, Styles.RING_ARCS[0][0], Styles.RING_ARCS[0][1]) + " " + Styles.arc(drum.c, drum.c, 92, Styles.RING_ARCS[1][0], Styles.RING_ARCS[1][1]) }
                        }
                        onObjectAdded: (index, object) => sunRing.data.push(object)
                    }
                }

                Repeater {
                    model: drum.chamberCount

                    delegate: Item {
                        id: slot

                        required property int index
                        readonly property var entry: drum.chambers[index]
                        readonly property var point: Styles.chamberPoint(index, drum.chamberCount, drum.style.orbit)
                        readonly property bool live: drum.liveIndex === index && !drum.spinning
                        readonly property real size: drum.style.chamberSize
                        readonly property bool ejecting: drum.ejectingIndex === index
                        // Rising edge only: the sequence runs to the end once started.
                        onEjectingChanged: if (slot.ejecting) ejectReload.start()

                        // The spent shell drops clear, the next round loads while it is out of sight, and it drops back in.
                        SequentialAnimation {
                            id: ejectReload
                            ParallelAnimation {
                                NumberAnimation { target: shell; property: "fallY"; to: 46; duration: 240; easing.type: Easing.InQuad }
                                NumberAnimation { target: shell; property: "wobble"; to: (slot.index % 2 === 0 ? 1 : -1) * 50; duration: 240; easing.type: Easing.InQuad }
                                NumberAnimation { target: shell; property: "opacity"; to: 0; duration: 220 }
                            }
                            ScriptAction { script: drum.swapChamber(slot.index) }
                            PropertyAction { target: shell; property: "fallY"; value: -46 }
                            PropertyAction { target: shell; property: "wobble"; value: 0 }
                            PauseAnimation { duration: 60 }
                            ParallelAnimation {
                                NumberAnimation { target: shell; property: "fallY"; to: 0; duration: 260; easing.type: Easing.OutBack }
                                NumberAnimation { target: shell; property: "opacity"; to: 1; duration: 200 }
                            }
                            ScriptAction { script: drum.ejectDone(slot.index) }
                        }

                        x: point.x - size / 2
                        y: point.y - size / 2
                        width: size
                        height: size

                        // A trail behind each chamber while the drum turns fast.
                        Shape {
                            x: -slot.x
                            y: -slot.y
                            width: drum.width
                            height: drum.height
                            visible: drum.spinSpeed > 0.08
                            opacity: Math.min(1, drum.spinSpeed * 1.4) * (drum.redSun ? 0.9 : 0.35)
                            ShapePath {
                                strokeWidth: drum.redSun ? 7 : slot.size * 0.5
                                strokeColor: drum.redSun ? drum.withAlpha(drum.colGlow, 0.55) : drum.withAlpha(drum.colAccent, 0.4)
                                capStyle: ShapePath.RoundCap
                                fillColor: "transparent"
                                PathSvg { path: Styles.arc(drum.c, drum.c, drum.style.orbit, slot.index * 360 / drum.chamberCount - drum.spinDirection * 34 * drum.spinSpeed, slot.index * 360 / drum.chamberCount) }
                            }
                        }

                        // Everything that moves when a spent chamber is ejected and reloaded.
                        Item {
                            id: shell
                            objectName: "shell"
                            property real fallY: 0
                            property real wobble: 0
                            anchors.fill: parent
                            // Counter-rotate so names stay upright as the drum turns.
                            rotation: -rotor.rotation
                            transform: [
                                Rotation { angle: shell.wobble; origin.x: shell.width / 2; origin.y: shell.height / 2 },
                                Translate { y: shell.fallY }
                            ]

                            // Glow round the live chamber.
                            Shape {
                                anchors.centerIn: parent
                                width: slot.size + 24
                                height: slot.size + 24
                                visible: slot.live || (drum.redSun && drum.ringLight > 0.05)
                                opacity: slot.live ? 1 : drum.ringLight * 0.6
                                ShapePath {
                                    strokeWidth: -1
                                    fillGradient: RadialGradient {
                                        centerX: (slot.size + 24) / 2; centerY: (slot.size + 24) / 2
                                        centerRadius: (slot.size + 24) / 2
                                        focalX: centerX; focalY: centerY
                                        GradientStop { position: 0.45; color: drum.withAlpha(drum.redSun ? drum.colGlow : drum.colAccent, drum.style.glow * 0.8) }
                                        GradientStop { position: 1.0; color: drum.withAlpha(drum.redSun ? drum.colGlow : drum.colAccent, 0) }
                                    }
                                    PathSvg { path: Styles.circle((slot.size + 24) / 2, (slot.size + 24) / 2, (slot.size + 24) / 2) }
                                }
                            }

                            // Red Sun: an ember bead, white-hot in the middle, riding on the ring.
                            Shape {
                                anchors.fill: parent
                                visible: drum.redSun
                                opacity: slot.live ? 1 : 0.6 + 0.4 * drum.ringLight
                                ShapePath {
                                    strokeWidth: -1
                                    fillGradient: RadialGradient {
                                        centerX: slot.size / 2; centerY: slot.size / 2
                                        centerRadius: slot.size / 2
                                        focalX: centerX; focalY: centerY
                                        GradientStop { position: 0.0; color: drum.colHot }
                                        GradientStop { position: 0.32; color: drum.colHot }
                                        GradientStop { position: 0.5; color: drum.colGlow }
                                        GradientStop { position: 1.0; color: drum.withAlpha(drum.colGlow, 0) }
                                    }
                                    PathSvg { path: Styles.circle(slot.size / 2, slot.size / 2, slot.size / 2) }
                                }
                            }

                            Shape {
                                id: chamberShape
                                anchors.fill: parent
                                visible: !drum.redSun
                                readonly property real h: slot.size / 2
                                readonly property color fill: slot.live ? drum.colAccent : drum.colChamber

                                function outline(inset) {
                                    const h = chamberShape.h, r = h - inset;
                                    switch (drum.style.chamber) {
                                    case "gem": return Styles.gem(h, h, r);
                                    case "squircle": return Styles.squircle(h, h, r, 4.6);
                                    case "star": return Styles.sparkle(h, h, r);
                                    default: return Styles.circle(h, h, r);
                                    }
                                }

                                // Body, with a gradient so it reads as a solid with depth.
                                ShapePath {
                                    strokeWidth: drum.redSun ? -1 : 1
                                    strokeColor: drum.style.chamber === "gem" ? drum.withAlpha("#ffffff", 0.55)
                                               : drum.withAlpha(Qt.darker(chamberShape.fill, 1.4), 0.9)
                                    fillGradient: LinearGradient {
                                        x1: 0; y1: 0; x2: slot.size * 0.3; y2: slot.size
                                        GradientStop { position: 0.0; color: drum.redSun ? drum.colHot
                                                                    : drum.withAlpha(Qt.lighter(chamberShape.fill, 1.35), drum.style.chamber === "gem" ? 0.42 : (slot.live ? 0.98 : 0.72)) }
                                        GradientStop { position: 1.0; color: drum.redSun ? (slot.live ? drum.colGlow : Qt.darker(drum.colGlow, 1.6))
                                                                    : drum.withAlpha(Qt.darker(chamberShape.fill, 1.15), drum.style.chamber === "gem" ? 0.22 : (slot.live ? 0.98 : 0.62)) }
                                    }
                                    PathSvg { path: chamberShape.outline(drum.redSun ? slot.size * 0.22 : 1) }
                                }
                                // The gem's flat top, and a specular line on every body.
                                ShapePath {
                                    strokeWidth: drum.style.chamber === "gem" ? 1 : 1.4
                                    strokeColor: drum.withAlpha("#ffffff", drum.style.chamber === "gem" ? 0.6 : (drum.redSun ? 0 : 0.22))
                                    fillColor: drum.style.chamber === "gem" ? drum.withAlpha("#ffffff", 0.1) : "transparent"
                                    capStyle: ShapePath.RoundCap
                                    PathSvg {
                                        path: drum.style.chamber === "gem" ? Styles.gemTable(chamberShape.h, chamberShape.h, chamberShape.h - 1)
                                            : Styles.arc(chamberShape.h, chamberShape.h, chamberShape.h - 4, -150, -40)
                                    }
                                }
                            }

                            Text {
                                anchors.fill: parent
                                anchors.margins: 6
                                visible: drum.style.names
                                text: slot.entry ? slot.entry.name : ""
                                font.family: drum.fontFamily
                                font.pixelSize: slot.live && drum.style.chamber !== "star" ? 9 : 8
                                font.bold: slot.live
                                color: slot.live ? (drum.colAccent.hslLightness > 0.6 ? "#1a1014" : "#ffffff") : drum.colOn
                                wrapMode: Text.WordWrap
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                                elide: Text.ElideRight
                                maximumLineCount: 3
                                style: Text.Raised
                                styleColor: drum.withAlpha("#000000", 0.25)
                            }
                        }
                    }
                }
            }

            // ── The hub ──────────────────────────────────────────────────────────

            Shape {
                anchors.fill: parent
                visible: drum.style.hub !== "void"
                ShapePath {
                    strokeWidth: 1.2
                    strokeColor: drum.withAlpha(drum.colOn, drum.style.hub === "prism" ? 0.6 : 0.35)
                    fillGradient: RadialGradient {
                        centerX: drum.c - 6; centerY: drum.c - 8
                        centerRadius: 30
                        focalX: drum.c - 6; focalY: drum.c - 8
                        GradientStop { position: 0.0; color: drum.style.hub === "prism" ? drum.withAlpha("#ffffff", 0.5) : Qt.lighter(drum.colChamber, 1.6) }
                        GradientStop { position: 1.0; color: drum.style.hub === "prism" ? drum.withAlpha(drum.colAccent, 0.18) : drum.colChamber }
                    }
                    PathSvg {
                        path: {
                            switch (drum.style.hub) {
                            case "squircle": return Styles.squircle(drum.c, drum.c, 24, 4.6);
                            case "prism": return Styles.gem(drum.c, drum.c, 22);
                            case "sparkle": return Styles.sparkle(drum.c, drum.c, 30);
                            default: return Styles.circle(drum.c, drum.c, 23);
                            }
                        }
                    }
                }
                ShapePath {
                    strokeWidth: -1
                    fillColor: drum.colAccent
                    PathSvg {
                        path: drum.style.hub === "sparkle" ? Styles.sparkle(drum.c, drum.c, 11)
                            : drum.style.hub === "prism" ? Styles.gemTable(drum.c, drum.c, 22)
                            : Styles.circle(drum.c, drum.c, 12)
                    }
                }
            }

            // ── The hammer and the pin at the top ────────────────────────────────

            Item {
                id: hammer
                objectName: "hammer"
                x: drum.c - 9
                y: drum.style.drum === "ring" ? -6 : (drum.style.drum === "rail" ? -18 : -14)
                width: 18
                height: 26
                transformOrigin: Item.Bottom

                Shape {
                    anchors.fill: parent
                    ShapePath {
                        strokeWidth: drum.redSun ? -1 : 1
                        strokeColor: drum.withAlpha(drum.colOn, 0.5)
                        fillGradient: LinearGradient {
                            x1: 0; y1: 0; x2: 18; y2: 26
                            GradientStop { position: 0.0; color: drum.redSun ? drum.colHot : Qt.lighter(drum.colAccent, 1.25) }
                            GradientStop { position: 1.0; color: drum.redSun ? drum.colGlow : Qt.darker(drum.colAccent, 1.2) }
                        }
                        PathSvg {
                            path: {
                                switch (drum.style.hammer) {
                                case "notch": return "M 9 26 L 4 12 L 14 12 Z";
                                case "shard": return "M 9 26 L 2 6 L 11 0 L 16 10 Z";
                                case "pill": return Styles.squircle(9, 13, 8, 4.6);
                                case "sparkle": return Styles.sparkle(9, 13, 10);
                                default: return "M 3 26 L 3 4 Q 3 1 6 1 L 12 1 Q 15 1 15 4 L 15 26 Z";
                                }
                            }
                        }
                    }
                }
            }

            // ── The safety bar while the screen is locked ────────────────────────

            Item {
                anchors.centerIn: parent
                visible: drum.locked
                width: parent.width * 1.05
                height: 26
                rotation: -8
                z: 20
                Rectangle {
                    anchors.fill: parent
                    radius: drum.style.drum === "squircle" ? 13 : 4
                    border.color: drum.withAlpha(drum.colOn, 0.4)
                    border.width: 1
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: drum.colChamber }
                        GradientStop { position: 0.5; color: drum.redSun ? drum.colGlow : drum.colBase }
                        GradientStop { position: 1.0; color: drum.colChamber }
                    }
                }
            }


        }
    }

    readonly property alias hammerItem: hammer
}
