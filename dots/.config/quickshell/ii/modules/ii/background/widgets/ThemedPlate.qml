pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Shapes
import "revolver/RevolverStyles.js" as Styles

/**
 * The plate behind a wallpaper widget, in the active Halcyon theme's shapes: the same look as the revolver's drum.
 *
 *   kind "disc"   a clock face: a glowing ring (Red Sun), a cut glass octagon (glass themes), a squircle (HyperNeo),
 *                 a gold rail (Star Rail), a keycap (the anime themes)
 *   kind "card"   a card: a dusk capsule with an ember edge, a cut stone, a squircle card, a gold-framed card, a keycap
 *
 * Drawn with QtQuick.Shapes only, in one multisampled layer, so it is smooth on any Qt 6.
 */
Item {
    id: plate

    property string themeId: ""
    property string kind: "disc"
    property color colBase: "#3a2c3c"
    property color colOn: "#f3e6e4"
    property color colAccent: "#ff8a7a"
    property color colGlow: "#ff4940"
    property color colHot: "#ffe2d6"
    /** 0..1, how strongly a Red Sun plate glows. */
    property real glow: 0.85

    readonly property var style: Styles.styleFor(themeId)
    readonly property bool redSun: style.id === "red-sun"
    readonly property bool keycap: style.plate === "keycap"
    // A keycap is solid ink, whatever the shell's transparency: the panel colour it is given is see-through when
    // transparency is on, which washed the cards out on the anime themes' white wallpapers.
    readonly property color solidBase: Qt.rgba(colBase.r, colBase.g, colBase.b, 1)
    readonly property real pad: 26

    function withAlpha(colour, alpha) {
        return Qt.rgba(colour.r, colour.g, colour.b, alpha);
    }

    Item {
        id: surface
        x: -plate.pad
        y: -plate.pad
        width: plate.width + 2 * plate.pad
        height: plate.height + 2 * plate.pad
        layer.enabled: true
        layer.samples: 4
        layer.smooth: true

        Item {
            x: plate.pad
            y: plate.pad
            width: plate.width
            height: plate.height

            // Keycap: a hard shadow straight down, the key's side showing under it.
            Shape {
                x: 0
                y: 6
                width: plate.width
                height: plate.height
                visible: plate.keycap
                ShapePath {
                    strokeWidth: 2.5
                    strokeColor: Qt.darker(plate.solidBase, 2.6)
                    fillColor: Qt.darker(plate.solidBase, 2.6)
                    PathSvg { path: Styles.plateOutline(plate.style, plate.kind, plate.width, plate.height, 2) }
                }
            }

            // Shadow under solid plates.
            Shape {
                anchors.fill: parent
                y: 5
                visible: !plate.keycap
                opacity: plate.redSun ? 0 : 0.3
                ShapePath {
                    strokeWidth: -1
                    fillColor: "#000000"
                    PathSvg { path: Styles.plateOutline(plate.style, plate.kind, plate.width, plate.height, 2) }
                }
            }

            // Red Sun: the ring's light round the plate.
            Shape {
                anchors.fill: parent
                visible: plate.redSun
                Instantiator {
                    model: [{ w: 34, a: 0.12 }, { w: 19, a: 0.28 }, { w: 9, a: 0.62 }]
                    delegate: ShapePath {
                        required property var modelData
                        strokeWidth: modelData.w
                        strokeColor: plate.withAlpha(plate.colGlow, modelData.a * plate.glow)
                        fillColor: "transparent"
                        PathSvg { path: Styles.plateOutline(plate.style, plate.kind, plate.width, plate.height, 3) }
                    }
                    onObjectAdded: (index, object) => sunGlow.data.push(object)
                }
                id: sunGlow
            }

            Shape {
                anchors.fill: parent
                ShapePath {
                    strokeWidth: plate.keycap ? 2.5 : plate.redSun ? 2.4 : (plate.style.drum === "rail" ? 2 : 1.2)
                    strokeColor: plate.keycap ? Qt.darker(plate.solidBase, 2.6)
                               : plate.redSun ? plate.colGlow
                               : plate.style.drum === "rail" ? plate.colAccent
                               : plate.style.drum === "facets" ? plate.withAlpha("#ffffff", 0.55)
                               : plate.withAlpha(plate.colOn, 0.14)
                    fillGradient: LinearGradient {
                        x1: 0; y1: 0; x2: plate.width * 0.35; y2: plate.height
                        GradientStop {
                            position: 0.0
                            color: plate.keycap ? Qt.lighter(plate.solidBase, 1.08)
                                 : plate.redSun ? plate.withAlpha("#1c1018", 0.78)
                                 : plate.style.drum === "facets" ? plate.withAlpha("#ffffff", 0.16)
                                 : Qt.lighter(plate.colBase, 1.16)
                        }
                        GradientStop {
                            position: 1.0
                            color: plate.keycap ? Qt.lighter(plate.solidBase, 1.08)
                                 : plate.redSun ? plate.withAlpha("#09060c", 0.86)
                                 : plate.style.drum === "facets" ? plate.withAlpha(plate.colAccent, 0.07)
                                 : Qt.darker(plate.colBase, 1.22)
                        }
                    }
                    PathSvg { path: Styles.plateOutline(plate.style, plate.kind, plate.width, plate.height, 2) }
                }
                // A thin hot line on Red Sun's edge, and a lit top edge on the others.
                ShapePath {
                    strokeWidth: plate.redSun ? 1 : 1.6
                    strokeColor: plate.keycap ? plate.withAlpha(plate.colOn, 0.78)
                               : plate.redSun ? plate.withAlpha(plate.colHot, 0.85) : plate.withAlpha("#ffffff", plate.style.drum === "facets" ? 0.3 : 0.12)
                    fillColor: "transparent"
                    PathSvg { path: Styles.plateOutline(plate.style, plate.kind, plate.width, plate.height, plate.redSun ? 2 : 5) }
                }
            }

            // Star Rail: an inner frame line; glass: two facet cuts.
            Shape {
                anchors.fill: parent
                visible: plate.style.drum === "rail" || plate.style.drum === "facets"
                ShapePath {
                    strokeWidth: 1
                    strokeColor: plate.style.drum === "rail" ? plate.withAlpha(plate.colAccent, 0.5) : plate.withAlpha("#ffffff", 0.22)
                    fillColor: "transparent"
                    PathSvg {
                        path: plate.style.drum === "rail" ? Styles.plateOutline(plate.style, plate.kind, plate.width, plate.height, 8)
                            : "M " + plate.width * 0.12 + " " + plate.height * 0.12 + " L " + plate.width * 0.62 + " " + plate.height * 0.98
                              + " M " + plate.width * 0.98 + " " + plate.height * 0.3 + " L " + plate.width * 0.4 + " " + plate.height * 0.02
                    }
                }
            }
        }
    }
}
