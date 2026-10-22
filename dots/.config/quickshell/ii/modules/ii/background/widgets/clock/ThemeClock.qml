pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Shapes
import "../revolver/RevolverStyles.js" as Styles

/**
 * A clock face of a theme's own, drawn the way its revolver is (CookieClock loads it in place of the usual face):
 *
 *   icey   After ICEY's cyan HUD: a see-through lens with a tick ring, a scanning arc that runs round the rim with
 *          the seconds (the minutes, without second precision), targeting brackets, chevron hands, a readout
 *   ink    Manga Ink's page: paper in a brush ensō with screentone, brush-stroke hands, bold numerals, a blush-pink
 *          heart in the middle, the date in a speech bubble, and a pink second hand with a heart on its tip
 *
 * Needs only QtQuick and RevolverStyles.js, so it can be drawn and tested on its own. Laid out on a 230 x 230 stage
 * and scaled, like the revolver's drum, and drawn into a texture as large as it is shown.
 */
Item {
    id: face

    property string kind: "icey"
    property date now: new Date()
    property bool showSeconds: true
    property color colAccent: "#5cd6f2"
    property color colAccent2: "#ffd86b"
    property color colOn: "#e4ecf7"
    property color colBase: "#080d18"
    property string fontFamily: ""
    /** How many screen pixels one stage pixel covers, times the screen's pixel ratio. */
    property real renderScale: width / 230

    readonly property real c: 115
    readonly property color ink: "#141414"
    readonly property color paper: "#f7f3ea"
    readonly property real hourAngle: ((now.getHours() % 12) + now.getMinutes() / 60) * 30
    readonly property real minuteAngle: (now.getMinutes() + now.getSeconds() / 60) * 6
    readonly property real secondAngle: now.getSeconds() * 6
    // The ICEY scanning arc: the seconds, or the minutes without second precision.
    readonly property real sweep: showSeconds ? now.getSeconds() / 60 : now.getMinutes() / 60

    function withAlpha(colour, alpha) {
        return Qt.rgba(colour.r, colour.g, colour.b, alpha);
    }
    function pad(n) {
        return n < 10 ? "0" + n : String(n);
    }

    implicitWidth: 230
    implicitHeight: 230

    // The face is laid out on 230 x 230, drawn on a surface a little larger so the brackets outside the dial are
    // not cut off.
    readonly property real margin: 14
    Item {
        id: surface
        x: -face.margin * face.width / 230
        y: x
        width: 230 + 2 * face.margin
        height: width
        scale: face.width / 230
        transformOrigin: Item.TopLeft
        layer.enabled: true
        layer.samples: 4
        layer.smooth: true
        layer.textureSize: Qt.size(Math.ceil(width * Math.max(1, face.renderScale)), Math.ceil(height * Math.max(1, face.renderScale)))

    Item {
        id: stage
        x: face.margin
        y: face.margin
        width: 230
        height: 230

        // ── After ICEY ─────────────────────────────────────────────────────────────
        Item {
            anchors.fill: parent
            visible: face.kind === "icey"

            Shape {
                anchors.fill: parent
                // The lens.
                ShapePath {
                    strokeWidth: 1.4
                    strokeColor: face.withAlpha(face.colAccent, 0.85)
                    fillGradient: RadialGradient {
                        centerX: face.c; centerY: face.c
                        centerRadius: 108
                        focalX: face.c; focalY: face.c - 24
                        // Nearly solid: the clock is read, and a bright wallpaper behind it washed it out.
                        GradientStop { position: 0.0; color: face.withAlpha(Qt.lighter(face.colBase, 1.5), 0.94) }
                        GradientStop { position: 0.8; color: face.withAlpha(face.colBase, 0.95) }
                        GradientStop { position: 0.97; color: face.withAlpha(face.colAccent, 0.22) }
                        GradientStop { position: 1.0; color: face.withAlpha(face.colAccent, 0.05) }
                    }
                    PathSvg { path: Styles.circle(face.c, face.c, 108) }
                }
                // Minute ticks, and the hours longer and lighter.
                ShapePath {
                    strokeWidth: 0.9
                    strokeColor: face.withAlpha(face.colAccent, 0.5)
                    fillColor: "transparent"
                    PathSvg { path: Styles.ticks(face.c, face.c, 99, 103.5, 60, -90) }
                }
                ShapePath {
                    strokeWidth: 2
                    strokeColor: face.withAlpha(face.colOn, 0.85)
                    fillColor: "transparent"
                    PathSvg { path: Styles.ticks(face.c, face.c, 92, 104, 12, -90) }
                }
                // The broken outer ring.
                ShapePath {
                    strokeWidth: 1
                    strokeColor: face.withAlpha(face.colOn, 0.5)
                    fillColor: "transparent"
                    PathSvg { path: Styles.arc(face.c, face.c, 114, -80, -10) + " " + Styles.arc(face.c, face.c, 114, 10, 80) + " " + Styles.arc(face.c, face.c, 114, 100, 170) + " " + Styles.arc(face.c, face.c, 114, 190, 260) }
                }
                // The scanning arc, from twelve to now, and its glow.
                ShapePath {
                    strokeWidth: 8
                    strokeColor: face.withAlpha(face.colAccent, 0.16)
                    fillColor: "transparent"
                    capStyle: ShapePath.FlatCap
                    PathSvg { path: face.sweep > 0.004 ? Styles.arc(face.c, face.c, 108, -90, -90 + 360 * face.sweep) : "" }
                }
                ShapePath {
                    strokeWidth: 2.6
                    strokeColor: Qt.lighter(face.colAccent, 1.3)
                    fillColor: "transparent"
                    capStyle: ShapePath.FlatCap
                    PathSvg { path: face.sweep > 0.004 ? Styles.arc(face.c, face.c, 108, -90, -90 + 360 * face.sweep) : "" }
                }
                // Targeting brackets, gold markers at three and nine.
                ShapePath {
                    strokeWidth: 2
                    strokeColor: face.withAlpha(face.colAccent, 0.95)
                    fillColor: "transparent"
                    joinStyle: ShapePath.MiterJoin
                    PathSvg { path: Styles.brackets(face.c, face.c, 118, 16) }
                }
                ShapePath {
                    strokeWidth: -1
                    fillColor: face.colAccent2
                    PathSvg { path: Styles.diamond(face.c - 114, face.c, 4) + " " + Styles.diamond(face.c + 114, face.c, 4) }
                }
                // A dashed inner ring.
                ShapePath {
                    strokeWidth: 1
                    strokeColor: face.withAlpha(face.colAccent, 0.35)
                    strokeStyle: ShapePath.DashLine
                    dashPattern: [4, 3]
                    fillColor: "transparent"
                    PathSvg { path: Styles.circle(face.c, face.c, 46) }
                }
            }

            // The readout: the date above the middle, the time below, as a HUD shows them.
            Text {
                y: 62
                width: 230
                horizontalAlignment: Text.AlignHCenter
                text: Qt.formatDate(face.now, "ddd dd").toUpperCase()
                color: face.withAlpha(face.colAccent, 0.9)
                font.family: face.fontFamily
                font.pixelSize: 11
                font.letterSpacing: 2.5
                font.weight: Font.DemiBold
            }
            Text {
                y: 146
                width: 230
                horizontalAlignment: Text.AlignHCenter
                text: face.pad(face.now.getHours()) + ":" + face.pad(face.now.getMinutes())
                color: face.colOn
                font.family: face.fontFamily
                font.pixelSize: 15
                font.letterSpacing: 3
                font.weight: Font.Bold
            }

            // Hour hand: a short bar with a chevron tip.
            Shape {
                anchors.fill: parent
                rotation: face.hourAngle
                ShapePath {
                    strokeWidth: 1.2
                    strokeColor: face.withAlpha(face.colAccent, 0.9)
                    fillColor: face.withAlpha(face.colOn, 0.92)
                    joinStyle: ShapePath.MiterJoin
                    PathSvg { path: "M 112 121 L 112 64 L 107 64 L 115 52 L 123 64 L 118 64 L 118 121 Z" }
                }
            }
            // Minute hand: long and thin, a hollow diamond near its tip.
            Shape {
                anchors.fill: parent
                rotation: face.minuteAngle
                ShapePath {
                    strokeWidth: 2.4
                    strokeColor: face.colAccent
                    fillColor: "transparent"
                    capStyle: ShapePath.RoundCap
                    PathSvg { path: "M 115 125 L 115 40" }
                }
                ShapePath {
                    strokeWidth: 1.6
                    strokeColor: face.colAccent
                    fillColor: face.withAlpha(face.colBase, 0.8)
                    PathSvg { path: Styles.diamond(face.c, 30, 7) }
                }
            }
            // The middle: a hexagon with the snowflake.
            Shape {
                anchors.fill: parent
                ShapePath {
                    strokeWidth: 1.4
                    strokeColor: face.colAccent
                    fillColor: face.withAlpha(face.colBase, 0.95)
                    PathSvg { path: Styles.polygon(face.c, face.c, 13, 6, 30) }
                }
                ShapePath {
                    strokeWidth: 1.1
                    strokeColor: Qt.lighter(face.colAccent, 1.25)
                    fillColor: "transparent"
                    capStyle: ShapePath.RoundCap
                    PathSvg { path: Styles.snowflake(face.c, face.c, 9) }
                }
            }
        }

        // ── Manga Ink ──────────────────────────────────────────────────────────────
        Item {
            anchors.fill: parent
            visible: face.kind === "ink"

            Shape {
                anchors.fill: parent
                ShapePath {
                    strokeWidth: -1
                    fillColor: face.paper
                    PathSvg { path: Styles.circle(face.c, face.c, 104) }
                }
                ShapePath {
                    strokeWidth: -1
                    fillColor: face.withAlpha(face.ink, 0.78)
                    PathSvg { path: Styles.screentone(face.c, face.c, 102, 6) }
                }
                Instantiator {
                    // The ensō, lifting at the upper right as the revolver's does.
                    model: [
                        { w: 11, a0: -12, a1: 246 }, { w: 8.5, a0: 244, a1: 262 }, { w: 6, a0: 260, a1: 276 },
                        { w: 3.6, a0: 274, a1: 288 }, { w: 1.8, a0: 286, a1: 298 },
                        { w: 8, a0: -22, a1: -10 }, { w: 4.5, a0: -30, a1: -20 }
                    ]
                    delegate: ShapePath {
                        required property var modelData
                        strokeWidth: modelData.w
                        strokeColor: face.ink
                        fillColor: "transparent"
                        capStyle: ShapePath.RoundCap
                        PathSvg { path: Styles.arc(face.c, face.c, 106, modelData.a0, modelData.a1) }
                    }
                    onObjectAdded: (index, object) => enso.data.push(object)
                }
                id: enso
                // Brush ticks for the hours between the numerals: thick at the rim, thinning inwards.
                ShapePath {
                    strokeWidth: 3.2
                    strokeColor: face.ink
                    fillColor: "transparent"
                    capStyle: ShapePath.RoundCap
                    PathSvg { path: [1, 2, 4, 5, 7, 8, 10, 11].map(h => Styles.ticks(face.c, face.c, 86, 94, 1, -90 + h * 30)).join(" ") }
                }
            }

            // Bold numerals at twelve, three, six and nine.
            Repeater {
                model: [{ n: "12", x: 115, y: 32 }, { n: "3", x: 198, y: 115 }, { n: "6", x: 115, y: 198 }, { n: "9", x: 32, y: 115 }]
                Text {
                    required property var modelData
                    x: modelData.x - width / 2
                    y: modelData.y - height / 2
                    text: modelData.n
                    color: face.ink
                    font.family: face.fontFamily
                    font.pixelSize: 22
                    font.weight: Font.Black
                }
            }

            // The date in a speech bubble at the lower right, its tail at the middle.
            Shape {
                anchors.fill: parent
                ShapePath {
                    strokeWidth: 2
                    strokeColor: face.ink
                    fillColor: "#ffffff"
                    PathSvg { path: Styles.bubble(152, 152, 19, 225) }
                }
            }
            Text {
                x: 152 - width / 2
                y: 152 - height / 2
                horizontalAlignment: Text.AlignHCenter
                text: Qt.formatDate(face.now, "ddd").toUpperCase() + "\n" + face.now.getDate()
                color: face.ink
                lineHeight: 0.85
                font.family: face.fontFamily
                font.pixelSize: 9
                font.weight: Font.Black
            }

            // Hour hand: a short, thick brush stroke.
            Shape {
                anchors.fill: parent
                rotation: face.hourAngle
                ShapePath {
                    strokeWidth: -1
                    fillColor: face.ink
                    PathSvg { path: "M 109 124 C 108 100, 111 78, 115 60 C 119 78, 122 100, 121 124 Z" }
                }
            }
            // Minute hand: a long, thinner one.
            Shape {
                anchors.fill: parent
                rotation: face.minuteAngle
                ShapePath {
                    strokeWidth: -1
                    fillColor: face.ink
                    PathSvg { path: "M 111 126 C 111 96, 113 60, 115 30 C 117 60, 119 96, 119 126 Z" }
                }
            }
            // Second hand: a pink line with a heart on its tip.
            Shape {
                anchors.fill: parent
                visible: face.showSeconds
                rotation: face.secondAngle
                ShapePath {
                    strokeWidth: 1.6
                    strokeColor: face.colAccent
                    fillColor: "transparent"
                    capStyle: ShapePath.RoundCap
                    PathSvg { path: "M 115 134 L 115 40" }
                }
                ShapePath {
                    strokeWidth: 1.2
                    strokeColor: face.ink
                    fillColor: face.colAccent
                    PathSvg { path: Styles.heart(face.c, 34, 6) }
                }
            }
            // The middle: a blush heart with a shine.
            Shape {
                anchors.fill: parent
                ShapePath {
                    strokeWidth: 2.2
                    strokeColor: face.ink
                    fillColor: face.colAccent
                    PathSvg { path: Styles.heart(face.c, face.c + 1, 11) }
                }
                ShapePath {
                    strokeWidth: -1
                    fillColor: face.paper
                    PathSvg { path: Styles.circle(face.c - 4, face.c - 3, 2) }
                }
            }
        }
    }
    }
}
