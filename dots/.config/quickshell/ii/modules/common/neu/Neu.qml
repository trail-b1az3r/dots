import QtQuick

/**
 * Halcyon Neumorph: a soft surface pressed out of the page (raised) or into it (inset), in the page's own colour,
 * lit from the top left (shaders/neumorph.frag). Put content inside it like any Item.
 *
 *   base      the material; the two shadows are made from it unless set
 *   inset     0 raised, 1 pressed in; animate it (pressed does) and the shape sinks smoothly
 *   convex    the face's own light: >0 a dome, <0 a dish
 *   accent    a colour laid into the face (a lit toggle, a gauge's fill), its alpha how much
 *
 * The shadows reach `margin` px beyond the item, so leave that much room round it.
 * Needs only QtQuick and the compiled shaders.
 */
Item {
    id: neu

    property color base: "#E3E8F0"
    property color lightTone: Qt.rgba(Math.min(1, base.r * 1.12 + 0.06), Math.min(1, base.g * 1.12 + 0.06),
                                      Math.min(1, base.b * 1.12 + 0.06), 0.95)
    property color darkTone: Qt.rgba(base.r * 0.72, base.g * 0.76, base.b * 0.84, 0.85)
    property color accent: "transparent"
    property real radius: Math.min(height / 2, 22)
    property real corner: 4.0
    property real distance: Math.max(3, Math.min(width, height) * 0.09)
    property real blur: distance * 1.6
    property real strength: 1.0
    property real convex: 0.0
    property bool pressed: false
    property real inset: pressed ? 1 : 0
    property point lightFrom: Qt.point(-0.707, -0.707)

    Behavior on inset {
        NumberAnimation { duration: 160; easing.type: Easing.OutCubic }
    }

    default property alias content: inner.data
    readonly property real margin: Math.ceil(distance + blur * 1.6)

    ShaderEffect {
        x: -neu.margin
        y: -neu.margin
        width: neu.width + 2 * neu.margin
        height: neu.height + 2 * neu.margin
        blending: true

        property vector2d itemSize: Qt.vector2d(width, height)
        property color base: neu.base
        property color lightTone: neu.lightTone
        property color darkTone: neu.darkTone
        property color accent: neu.accent
        property vector2d lightDir: Qt.vector2d(neu.lightFrom.x, neu.lightFrom.y).normalized()
        property real margin: neu.margin
        property real radius: neu.radius
        property real corner: neu.corner
        property real distance: neu.distance
        property real blur: neu.blur
        property real strength: neu.strength
        property real inset: neu.inset
        property real convex: neu.convex
        vertexShader: Qt.resolvedUrl("shaders/neu.vert.qsb")
        fragmentShader: Qt.resolvedUrl("shaders/neumorph.frag.qsb")
    }

    Item {
        id: inner
        anchors.fill: parent
    }
}
