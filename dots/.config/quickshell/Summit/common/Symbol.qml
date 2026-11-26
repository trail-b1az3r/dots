import QtQuick
import qs.common

// A Material Symbols Rounded glyph, by its name: "wifi", "volume_up", ... (Summit's bundled cut of the font: Theme.iconFont).
// A new icon is added to assets/fonts/SummitSymbols-vN.ttf (assets/README.md). A name the font has no icon for would be
// drawn as the word itself, in whatever font stands in, spilling over everything round it: then it draws nothing.
Text {
    id: root
    property string name
    property real fill: 0
    property int size: 19
    property int weight: 500
    // An icon is one glyph about as wide as it is tall; a name without one is a row of letters.
    readonly property bool known: metrics.advanceWidth > 0 && metrics.advanceWidth <= root.size * 1.6
    text: known ? name : ""
    font.family: Theme.iconFont
    font.pixelSize: size
    // Both: the weight picks the font's instance where the axes are not applied (the Thin default otherwise).
    font.weight: root.weight
    font.variableAxes: { "FILL": root.fill, "wght": root.weight, "opsz": 24 }
    color: Theme.text
    verticalAlignment: Text.AlignVCenter
    horizontalAlignment: Text.AlignHCenter
    renderType: Text.QtRendering

    TextMetrics {
        id: metrics
        font.family: Theme.iconFont
        font.pixelSize: root.size
        text: root.name
    }
}
