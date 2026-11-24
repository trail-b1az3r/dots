import QtQuick
import qs.common

// Frosted glass: every Summit surface. A thin neutral tint, as light or dark as the theme's surface but without its hue
// (Hyprland blurs what is behind it: the layer rules halcyon-theme writes), and a soft light from the top. No edge.
Rectangle {
    id: root
    property real tint: Theme.glassTint
    property real highlight: 0.10
    radius: Theme.radius
    color: Theme.alpha(Theme.glass, root.tint)

    // The light from above: a whisper of white fading out halfway down.
    Rectangle {
        anchors.fill: parent
        radius: root.radius
        gradient: Gradient {
            GradientStop { position: 0.0; color: Theme.alpha("#FFFFFF", root.highlight) }
            GradientStop { position: 0.55; color: Theme.alpha("#FFFFFF", 0.0) }
        }
    }
}
