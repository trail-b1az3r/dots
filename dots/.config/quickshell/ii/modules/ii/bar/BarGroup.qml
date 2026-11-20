import qs.modules.common
import qs.modules.common.widgets
import QtQuick
import QtQuick.Layouts
import "../../common/neu"

Item {
    id: root
    property bool vertical: false
    property real padding: 5
    implicitWidth: vertical ? Appearance.sizes.baseVerticalBarWidth : (gridLayout.implicitWidth + padding * 2)
    implicitHeight: vertical ? (gridLayout.implicitHeight + padding * 2) : Appearance.sizes.baseBarHeight
    default property alias items: gridLayout.children
    // Islands (bar corner style 3): each group floats as a pill of its own, with a shadow, since there is no bar
    // strip behind it.
    readonly property bool island: (Config.options?.bar.cornerStyle ?? 0) === 3 && !vertical
        && !(Config.options?.bar.borderless ?? false) && (Config.options?.bar.showBackground ?? true)

    // Neumorph's islands are pressed out of the page instead: no edge, two soft shadows of its own.
    readonly property bool neu: island && (Config.options?.halcyon.theme ?? "") === "neumorph"

    StyledRectangularShadow {
        target: background
        visible: root.island && !root.neu && (Config.options?.bar.floatStyleShadow ?? true)
    }
    Neu {
        anchors.fill: background
        visible: root.neu
        base: Qt.rgba(Appearance.colors.colLayer0.r, Appearance.colors.colLayer0.g, Appearance.colors.colLayer0.b, 1)
        radius: height / 2
        corner: 2.0   // round ends: a pill, not a squircle
        distance: 3
        convex: 0.35
    }

    Rectangle {
        id: background
        anchors {
            fill: parent
            topMargin: root.vertical || root.island ? 0 : 4
            bottomMargin: root.vertical || root.island ? 0 : 4
            leftMargin: root.vertical ? 4 : 0
            rightMargin: root.vertical ? 4 : 0
        }
        // Manga Ink: no box round each group (a box in a box, on the bar's panel); gutters part them instead.
        readonly property bool manga: Appearance.squareBar && !root.vertical
        color: root.neu ? "transparent" : root.island ? Appearance.colors.colLayer0
             : Config.options?.bar.borderless || manga ? "transparent" : Appearance.colors.colLayer1
        radius: root.island ? height / 2 : Appearance.squareBar ? 0 : Appearance.rounding.small
        // Halcyon themes edge each group in their own light: Red Sun's ember, Star Rail's gold, glass's frost.
        readonly property string theme: Config.options?.halcyon.theme ?? ""
        border.width: root.neu ? 0 : root.island ? 1 : Config.options?.bar.borderless || manga ? 0 : Appearance.squareBar ? 2 : (edgeColour.a > 0 ? 1 : 0)
        border.color: root.island && edgeColour.a === 0 ? Appearance.colors.colLayer0Border : edgeColour
        readonly property color edgeColour: {
            switch (theme) {
            case "red-sun": return Qt.rgba(1.0, 0.29, 0.25, 0.42);
            case "silence": return Qt.rgba(Appearance.colors.colPrimary.r, Appearance.colors.colPrimary.g, Appearance.colors.colPrimary.b, 0.24);
            case "after-icey":
            case "manga-ink":
            case "manga-ink-dark": return Appearance.colors.colOnLayer1;   // ink
            case "hsr": return Qt.rgba(Appearance.colors.colPrimary.r, Appearance.colors.colPrimary.g, Appearance.colors.colPrimary.b, 0.38);
            case "shattered-glass":
            case "fractured-glass": return Qt.rgba(1, 1, 1, 0.16);
            default: return "transparent";
            }
        }
    }

    // Manga Ink's gutters: an ink rule at each side of the group, so two groups side by side are parted the way manga
    // panels are, by a strip of paper between two rules.
    Repeater {
        model: background.manga && !(Config.options?.bar.borderless ?? false) ? 2 : 0
        delegate: Rectangle {
            required property int index
            x: index === 0 ? 0 : root.width - width
            anchors.verticalCenter: root.verticalCenter
            width: 2
            height: root.height - 14
            color: Appearance.colors.colOnLayer1
        }
    }

    GridLayout {
        id: gridLayout
        columns: root.vertical ? 1 : -1
        anchors {
            verticalCenter: root.vertical ? undefined : parent.verticalCenter
            horizontalCenter: root.vertical ? parent.horizontalCenter : undefined
            left: root.vertical ? undefined : parent.left
            right: root.vertical ? undefined : parent.right
            top: root.vertical ? parent.top : undefined
            bottom: root.vertical ? parent.bottom : undefined
            margins: root.padding
        }
        columnSpacing: 4
        rowSpacing: 12
    }
}