import QtQuick
import qs.Config

/**
 * The standard button.
 *
 * Three looks from one component, because a desktop with three button
 * implementations ends up with three different corner radii:
 *   · filled — the accent-coloured primary action
 *   · tinted — a glass pill, the default
 *   · plain  — text only, for tertiary actions
 */
Item {
    id: root

    property string text: ""
    property string glyph: ""
    property string icon: ""
    /** filled | tinted | plain */
    property string variant: "tinted"
    property bool enabled: true
    property bool destructive: false
    property int radius: Theme.radiusSm
    property int horizontalPadding: Theme.spacingLg
    property alias font: label.font

    signal clicked

    readonly property color accentColor: root.destructive ? Theme.danger : Theme.accent

    implicitHeight: 34
    implicitWidth: row.implicitWidth + root.horizontalPadding * 2

    opacity: root.enabled ? 1.0 : 0.45

    Rectangle {
        id: background
        anchors.fill: parent
        radius: root.radius
        color: {
            if (root.variant === "filled")
                return state.pressed ? Qt.darker(root.accentColor, 1.12) : root.accentColor;
            if (root.variant === "tinted")
                return Theme.surfaceRaised;
            return "transparent";
        }
        border.width: root.variant === "tinted" ? 1 : 0
        border.color: Theme.glassBorder

        Behavior on color {
            enabled: Theme.animationsEnabled
            ColorAnimation { duration: Theme.durInstant }
        }
    }

    Row {
        id: row
        anchors.centerIn: parent
        spacing: Theme.spacingSm

        Icon {
            anchors.verticalCenter: parent.verticalCenter
            visible: root.icon.length > 0 || root.glyph.length > 0
            source: root.icon
            glyph: root.glyph
            size: Theme.sizeBodyLarge
            color: label.color
        }

        Label {
            id: label
            anchors.verticalCenter: parent.verticalCenter
            visible: root.text.length > 0
            text: root.text
            variant: "body"
            font.weight: Theme.weightMedium
            color: {
                if (root.variant === "filled")
                    return Theme.onAccent;
                if (root.destructive)
                    return Theme.danger;
                return Theme.text;
            }
        }
    }

    StateLayer {
        anchors.fill: parent
        radius: root.radius
        enabled: root.enabled
        focusVisible: root.activeFocus
        onClicked: root.clicked()
    }

    Keys.onReturnPressed: root.clicked()
    Keys.onSpacePressed: root.clicked()

    // Screen readers read this rather than the pile of Rectangles.
    Accessible.role: Accessible.Button
    Accessible.name: root.text
    Accessible.onPressAction: root.clicked()
}
