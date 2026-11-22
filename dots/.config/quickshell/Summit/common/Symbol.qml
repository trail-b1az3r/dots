import QtQuick
import qs.common

// A Material Symbols Rounded glyph (the icon font Halcyon installs), by its name: "wifi", "volume_up", ...
Text {
    id: root
    property string name
    property real fill: 0
    property int size: 19
    property int weight: 500
    text: name
    font.family: Theme.iconFont
    font.pixelSize: size
    // Both: the weight picks the font's instance where the axes are not applied (the Thin default otherwise).
    font.weight: root.weight
    font.variableAxes: { "FILL": root.fill, "wght": root.weight, "opsz": 24 }
    color: Theme.text
    verticalAlignment: Text.AlignVCenter
    horizontalAlignment: Text.AlignHCenter
    renderType: Text.QtRendering
}
