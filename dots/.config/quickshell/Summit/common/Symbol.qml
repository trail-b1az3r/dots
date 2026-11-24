import QtQuick
import qs.common

// A Material Symbols Rounded glyph, by its name: "wifi", "volume_up", ... (Summit's bundled cut of the font: Theme.iconFont).
// A name that is not in it shows as text, so a new icon is added to assets/fonts/SummitSymbols.ttf (assets/README.md).
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
