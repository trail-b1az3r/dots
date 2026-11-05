import qs.modules.common
import QtQuick
import QtQuick.Layouts

Item {
    id: root
    property bool vertical: false
    property real padding: 5
    implicitWidth: vertical ? Appearance.sizes.baseVerticalBarWidth : (gridLayout.implicitWidth + padding * 2)
    implicitHeight: vertical ? (gridLayout.implicitHeight + padding * 2) : Appearance.sizes.baseBarHeight
    default property alias items: gridLayout.children

    Rectangle {
        id: background
        anchors {
            fill: parent
            topMargin: root.vertical ? 0 : 4
            bottomMargin: root.vertical ? 0 : 4
            leftMargin: root.vertical ? 4 : 0
            rightMargin: root.vertical ? 4 : 0
        }
        // Manga Ink: no box round each group (a box in a box, on the bar's panel); gutters part them instead.
        readonly property bool manga: Appearance.squareBar && !root.vertical
        color: Config.options?.bar.borderless || manga ? "transparent" : Appearance.colors.colLayer1
        radius: Appearance.squareBar ? 0 : Appearance.rounding.small
        // Halcyon themes edge each group in their own light: Red Sun's ember, Star Rail's gold, glass's frost.
        readonly property string theme: Config.options?.halcyon.theme ?? ""
        border.width: Config.options?.bar.borderless || manga ? 0 : Appearance.squareBar ? 2 : (edgeColour.a > 0 ? 1 : 0)
        border.color: edgeColour
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