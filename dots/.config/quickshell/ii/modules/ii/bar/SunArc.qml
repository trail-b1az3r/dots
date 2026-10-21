pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Shapes

/**
 * The sun dial's drawing: today's arc from sunrise (left) to sunset (right) over a horizon line, with the sun on it.
 * At night the dial turns upside down, the arc hanging under the horizon, and the moon travels along it from where
 * the sun set (right) back to where it will rise (left), drawn as tonight's phase (a crescent, a half, a full disc...). Without a location
 * (progress undefined) only a faint arc is drawn.
 *
 * Needs only QtQuick, so it can be drawn and tested on its own.
 */
Item {
    id: arc

    /** 0 at sunrise, 1 at sunset; below 0 before dawn, above 1 after dusk; undefined when unknown. */
    property var progress: undefined
    /** How long today's daylight is, in hours: progress is in days of daylight, so it says how long the night is. */
    property real dayHours: 12
    /** Where the moon is in its month: 0 new, 0.25 first quarter, 0.5 full, 0.75 last quarter. */
    property real moonPhase: arc.moonPhaseAt(new Date())
    /** South of the equator the moon is lit from the other side. */
    property bool southern: false
    property color colLine: "#80ffffff"
    property color colSun: "#ffc18a"
    property color colGlow: "#ff4940"
    property color colMoon: "#e8ecf4"
    /** Red Sun: the sun is a ring, like the one in the wallpaper. */
    property bool ring: false

    readonly property bool known: progress !== undefined && progress !== null && !isNaN(progress)
    readonly property bool daytime: known && progress >= 0 && progress <= 1
    readonly property bool night: known && !daytime
    readonly property real t: known ? Math.max(0, Math.min(1, progress)) : 0.5
    // How far through the night: 0 at sunset, 1 at the next sunrise.
    readonly property real nightLength: Math.max(0.01, (24 - dayHours) / Math.max(0.01, dayHours))
    readonly property real nightT: !night ? 0 : Math.max(0, Math.min(1,
        progress > 1 ? (progress - 1) / nightLength : 1 + progress / nightLength))
    readonly property real cx: width / 2
    readonly property real baseY: height - 4
    readonly property real r: Math.min(width / 2 - 3, height - 7)
    // Where the sun (by day) or the moon (by night) is, in the dial's own upright drawing. At night that drawing is
    // turned upside down, so the moon is shown at (sunX, height - sunY).
    readonly property real pos: daytime ? t : 1 - nightT
    readonly property real sunX: cx - r * Math.cos(Math.PI * pos)
    readonly property real sunY: baseY - r * Math.sin(Math.PI * pos)
    readonly property real moonX: sunX
    readonly property real moonY: height - sunY
    /** 1 upright, -1 upside down; it turns over at sunset and sunrise. */
    property real flip: night ? -1 : 1
    Behavior on flip {
        NumberAnimation { duration: 700; easing.type: Easing.InOutCubic }
    }

    /** The moon's phase on a date, from the mean synodic month and a known new moon (6 Jan 2000, 18:14 UTC). */
    function moonPhaseAt(date) {
        const synodic = 29.530588853;
        const days = (date.getTime() - Date.UTC(2000, 0, 6, 18, 14)) / 86400000;
        const phase = (days / synodic) % 1;
        return phase < 0 ? phase + 1 : phase;
    }
    /** How much of the moon's face is lit, 0 to 1. */
    function moonLit(phase) {
        return (1 - Math.cos(2 * Math.PI * phase)) / 2;
    }
    /** new, waxing-crescent, first-quarter, waxing-gibbous, full, waning-gibbous, last-quarter, waning-crescent */
    function moonName(phase) {
        const names = ["new", "waxing-crescent", "first-quarter", "waxing-gibbous", "full", "waning-gibbous",
                       "last-quarter", "waning-crescent"];
        return names[Math.floor(((phase % 1) * 8) + 0.5) % 8];
    }

    implicitWidth: 34
    implicitHeight: 22

    layer.enabled: true
    layer.samples: 4

    Shape {
        anchors.fill: parent
        transform: Scale {
            origin.y: arc.height / 2
            yScale: arc.flip
        }
        // The horizon.
        ShapePath {
            strokeWidth: 1
            strokeColor: arc.colLine
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            startX: 1; startY: arc.baseY
            PathLine { x: arc.width - 1; y: arc.baseY }
        }
        // The rest of the day (or night), dotted.
        ShapePath {
            strokeWidth: 1.2
            strokeColor: arc.colLine
            strokeStyle: ShapePath.DashLine
            dashPattern: [1.5, 2.5]
            fillColor: "transparent"
            startX: arc.cx - arc.r; startY: arc.baseY
            PathArc { x: arc.cx + arc.r; y: arc.baseY; radiusX: arc.r; radiusY: arc.r }
        }
        // The part already gone, solid.
        ShapePath {
            strokeWidth: 1.6
            strokeColor: !arc.known ? "transparent" : arc.daytime ? arc.colSun
                : Qt.rgba(arc.colMoon.r, arc.colMoon.g, arc.colMoon.b, 0.7)
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            // By day from sunrise (left); by night from sunset (right), the other way round.
            startX: arc.night ? arc.cx + arc.r : arc.cx - arc.r; startY: arc.baseY
            PathArc {
                x: arc.sunX; y: arc.sunY; radiusX: arc.r; radiusY: arc.r
                direction: arc.night ? PathArc.Counterclockwise : PathArc.Clockwise
            }
        }
    }

    // The sun: a glow, then the disc (or ring).
    Rectangle {
        x: arc.sunX - width / 2
        y: arc.sunY - height / 2
        width: 12
        height: 12
        radius: 6
        visible: arc.daytime
        color: Qt.rgba(arc.colGlow.r, arc.colGlow.g, arc.colGlow.b, 0.35)
    }
    Rectangle {
        x: arc.sunX - width / 2
        y: arc.sunY - height / 2
        width: arc.ring ? 8 : 6
        height: width
        radius: width / 2
        visible: arc.daytime
        color: arc.ring ? "transparent" : arc.colSun
        border.width: arc.ring ? 1.6 : 0
        border.color: arc.colSun
    }

    // The moon, in tonight's phase: the dark face faintly, then the lit part.
    Rectangle {
        x: arc.moonX - width / 2
        y: arc.moonY - height / 2
        width: 14
        height: 14
        radius: 7
        visible: arc.night
        color: Qt.rgba(arc.colMoon.r, arc.colMoon.g, arc.colMoon.b, 0.06 + 0.16 * arc.moonLit(arc.moonPhase))
    }
    Canvas {
        id: moon
        x: arc.moonX - width / 2
        y: arc.moonY - height / 2
        width: 11
        height: 11
        visible: arc.night
        renderStrategy: Canvas.Immediate
        onPaint: {
            const ctx = getContext("2d");
            ctx.reset();
            const c = width / 2, rad = width / 2 - 0.5;
            // The dark face, so a new moon still shows where it is.
            ctx.beginPath();
            ctx.arc(c, c, rad, 0, 2 * Math.PI);
            ctx.fillStyle = Qt.rgba(arc.colMoon.r, arc.colMoon.g, arc.colMoon.b, 0.18);
            ctx.fill();
            // The lit part: the limb on the lit side, back along the terminator (an ellipse's half).
            const phase = arc.moonPhase;
            let right = phase < 0.5;                      // waxing: lit on the right, in the north
            if (arc.southern)
                right = !right;
            // The terminator's width: on the limb when new (nothing lit), straight at the quarters, on the far limb
            // when full.
            const k = Math.cos(2 * Math.PI * phase);
            const side = right ? 1 : -1;
            ctx.beginPath();
            for (let i = 0; i <= 24; i++) {             // the limb, top to bottom
                const a = -Math.PI / 2 + Math.PI * i / 24;
                ctx.lineTo(c + side * rad * Math.cos(a), c + rad * Math.sin(a));
            }
            for (let i = 24; i >= 0; i--) {             // the terminator, bottom to top
                const a = -Math.PI / 2 + Math.PI * i / 24;
                ctx.lineTo(c + side * k * rad * Math.cos(a), c + rad * Math.sin(a));
            }
            ctx.closePath();
            ctx.fillStyle = arc.colMoon;
            ctx.fill();
        }
        Connections {
            target: arc
            function onMoonPhaseChanged() { moon.requestPaint(); }
            function onSouthernChanged() { moon.requestPaint(); }
            function onColMoonChanged() { moon.requestPaint(); }
            function onNightChanged() { moon.requestPaint(); }
        }
    }
}
