import QtQuick
import qs.Config
import qs.Components

/**
 * The bar's single tooltip.
 *
 * Drawn inside the bar's own window rather than as a popup surface: a
 * tooltip is a hint, and a hint is not worth a Wayland surface, an
 * exclusive zone negotiation and a focus question. It sits just past the
 * bar's edge, clipped only by the bar's height, which is why the bar
 * leaves room for it.
 */
Item {
    id: root

    required property var surface
    property string text: ""
    property var anchorItem: null
    /** True when the bar is at the top, so the tooltip hangs below it. */
    property bool below: true

    readonly property bool shown: root.text !== "" && root.anchorItem !== null

    parent: root.surface
    z: 100
    width: bubble.width
    height: bubble.height
    visible: opacity > 0
    opacity: root.shown ? 1 : 0

    x: {
        if (!root.anchorItem || !root.surface) {
            return 0;
        }
        const centre = root.anchorItem.mapToItem(
            root.surface, root.anchorItem.width / 2, 0).x;
        const half = bubble.width / 2;
        // Keep it on screen at either end of the bar.
        return Math.max(
            Theme.spacingXs,
            Math.min(root.surface.width - bubble.width - Theme.spacingXs,
                     centre - half));
    }

    y: root.below ? root.surface.height + Theme.spacingXs
        : -bubble.height - Theme.spacingXs

    Behavior on opacity {
        enabled: Theme.animationsEnabled
        NumberAnimation {
            duration: Theme.durQuick
            easing.type: Easing.Bezier
            easing.bezierCurve: Theme.curve("standard")
        }
    }

    GlassSurface {
        id: bubble

        level: 4
        radius: Theme.radiusSm
        padding: 0
        implicitWidth: label.implicitWidth + Theme.spacingMd * 2
        implicitHeight: label.implicitHeight + Theme.spacingSm * 2

        Text {
            id: label

            anchors.centerIn: parent
            text: root.text
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeFootnote
            textFormat: Text.PlainText
        }
    }
}
