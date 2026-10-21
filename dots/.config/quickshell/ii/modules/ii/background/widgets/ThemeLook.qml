import QtQuick
import qs.modules.common
import "revolver/RevolverStyles.js" as Styles

/**
 * The active Halcyon theme's look for a wallpaper widget's insides (RevolverStyles.lookFor): which gauge, bars,
 * progress line and lyric style to draw, and the colours to draw them in. Colours a theme does not fix follow the
 * palette, so a theme's own colours (or the wallpaper's, with no theme) still come through.
 */
QtObject {
    id: look

    property string themeId: Config.options?.halcyon.theme ?? ""
    readonly property var spec: Styles.lookFor(themeId)
    readonly property string id: spec.id

    readonly property color accentA: spec.colorA !== "" ? spec.colorA : Appearance.colors.colPrimary
    readonly property color accentB: spec.colorB !== "" ? spec.colorB : Appearance.colors.colTertiary
    readonly property color accentC: spec.colorA !== "" ? Qt.lighter(spec.colorB, 1.25) : Appearance.colors.colSecondary
    readonly property color text: spec.text !== "" ? spec.text : Appearance.colors.colOnLayer1
    readonly property color subtext: spec.text !== "" ? Qt.rgba(look.text.r, look.text.g, look.text.b, 0.62) : Appearance.colors.colSubtext
    readonly property color glow: spec.glow !== "" ? spec.glow : accentA
    readonly property color track: Qt.rgba(accentA.r, accentA.g, accentA.b, 0.16)
    readonly property real spacing: spec.spacing
    /** The card's colour, solid: the panel colour is see-through when the shell's transparency is on, which washed
     *  keycaps and their shadows out over a bright wallpaper. */
    readonly property color card: Qt.rgba(Appearance.colors.colLayer1.r, Appearance.colors.colLayer1.g, Appearance.colors.colLayer1.b, 1)

    /** A label as the theme sets them: Red Sun, Star Rail and the keycaps in capitals. */
    function label(text) {
        return spec.caps ? String(text).toUpperCase() : String(text);
    }
}
