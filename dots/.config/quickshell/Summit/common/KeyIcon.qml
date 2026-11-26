import QtQuick
import QtQuick.Shapes
import qs.common

// Summit's own icons for the modifier keys, drawn as strokes on a 24 x 24 grid in the theme's colour:
//   super  the mountain (Summit's mark: Super is Halcyon's key)
//   ctrl   a caret, as Ctrl is written ^
//   shift  a hollow arrow up
//   alt    the option sign: a step down and a bar
//   fn     the letters fn
//   hyper  a four-point star: all four modifiers at once
Item {
    id: root
    property string kind: "super"
    property color color: Theme.text
    property real size: 16
    property real stroke: 2

    readonly property var paths: ({
        "super": ["M2.5 19 L9 7.5 L12.6 13.4 L15.2 10 L21.5 19 Z", "M7 11.3 L9 13 L11 11.3"],
        "ctrl": ["M5.5 15.5 L12 8 L18.5 15.5"],
        "shift": ["M12 3.5 L20.5 12 L15.75 12 L15.75 20.5 L8.25 20.5 L8.25 12 L3.5 12 Z"],
        "alt": ["M3 7 L8.5 7 L15 17 L21 17", "M14 7 L21 7"],
        "fn": ["M10 20 L10 9.5 Q10 5 14 5", "M6.5 11 L13 11", "M15 20 L15 11.5", "M15 14.5 Q15 11.5 18 11.5 Q21 11.5 21 14.5 L21 20"],
        "hyper": ["M12 2.5 L14.2 9.8 L21.5 12 L14.2 14.2 L12 21.5 L9.8 14.2 L2.5 12 L9.8 9.8 Z"]
    })
    readonly property var parts: root.paths[root.kind] ?? []
    // Strokes in the grid's units, so they stay this thick at any size.
    readonly property real width24: root.stroke * 24 / root.size

    implicitWidth: size
    implicitHeight: size

    Shape {
        width: 24
        height: 24
        scale: root.size / 24
        transformOrigin: Item.TopLeft
        preferredRendererType: Shape.CurveRenderer

        // Up to four strokes an icon; the ones an icon does not use draw nothing.
        Part { index: 0 }
        Part { index: 1 }
        Part { index: 2 }
        Part { index: 3 }
    }

    component Part: ShapePath {
        required property int index
        strokeColor: index < root.parts.length ? root.color : "transparent"
        strokeWidth: root.width24
        fillColor: "transparent"
        capStyle: ShapePath.RoundCap
        joinStyle: ShapePath.RoundJoin
        PathSvg { path: index < root.parts.length ? root.parts[index] : "M0 0" }
    }
}
