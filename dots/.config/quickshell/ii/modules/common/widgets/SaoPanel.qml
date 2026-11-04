import QtQuick

/**
 * A Sword Art Online menu panel, for the Sword Art Online theme's popups and menus (the bar's popups, the tray's
 * menus): the game's slate glass in a fine light edge, an orange rule along the top that is brightest in the middle,
 * a white notch in each top corner, and the small pointer on the side it opened from, as the game's panels unfold
 * from the button chosen.
 *
 * Put it behind the content, filling the panel; the panel's own background goes transparent.
 */
Item {
    id: panel

    /** Where the pointer sits: "top", "bottom" or "" for none. */
    property string pointer: "top"
    /** Its position along that edge, 0 to 1. */
    property real pointerAt: 0.5

    readonly property color orange: "#F5A43B"
    readonly property color white: "#F4F6F8"

    // Typed, so a "#RRGGBB" string is made a colour first: an untyped string has no .r, and came out black.
    function withAlpha(colour: color, alpha: real): color {
        return Qt.rgba(colour.r, colour.g, colour.b, alpha);
    }

    // The pointer: a small square turned on its corner, half out of the panel.
    Rectangle {
        visible: panel.pointer !== ""
        width: 12
        height: 12
        rotation: 45
        x: Math.max(12, Math.min(panel.width - 24, panel.width * panel.pointerAt - 6))
        y: panel.pointer === "bottom" ? panel.height - 6 : -6
        color: panel.pointer === "bottom" ? "#161B22" : "#28313C"
        border.width: 1
        border.color: panel.withAlpha("#FFFFFF", 0.18)
    }
    Rectangle {
        anchors.fill: parent
        radius: 4
        gradient: Gradient {
            GradientStop { position: 0.0; color: panel.withAlpha("#28313C", 0.97) }
            GradientStop { position: 1.0; color: panel.withAlpha("#161B22", 0.98) }
        }
        border.width: 1
        border.color: panel.withAlpha("#FFFFFF", 0.16)
    }
    // A lighter band under the top edge, like light on the glass.
    Rectangle {
        x: 1
        y: 1
        width: parent.width - 2
        height: Math.min(18, parent.height / 3)
        radius: 3
        gradient: Gradient {
            GradientStop { position: 0.0; color: panel.withAlpha("#FFFFFF", 0.07) }
            GradientStop { position: 1.0; color: panel.withAlpha("#FFFFFF", 0) }
        }
    }
    // The orange rule.
    Rectangle {
        anchors.top: parent.top
        anchors.topMargin: 1
        anchors.horizontalCenter: parent.horizontalCenter
        width: parent.width * 0.62
        height: 2
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: panel.withAlpha(panel.orange, 0) }
            GradientStop { position: 0.5; color: panel.orange }
            GradientStop { position: 1.0; color: panel.withAlpha(panel.orange, 0) }
        }
    }
    // The notches.
    Repeater {
        model: 2
        Rectangle {
            required property int index
            width: 6
            height: 6
            rotation: 45
            x: index === 0 ? 7 : panel.width - 13
            y: 7
            color: panel.withAlpha(panel.white, 0.85)
            visible: panel.width > 60
        }
    }
}
