import QtQuick
import QtQuick.Layouts
import qs.Config
import qs.Components
import qs.Services

/**
 * The bar's glass panel and its three sections.
 *
 * The centre section is genuinely centred on the bar, not placed after
 * the left one: a clock that drifts sideways as the window title grows
 * is the tell of a bar laid out as one row. Left and right are given
 * the space that remains and elide rather than push the centre.
 */
Item {
    id: root

    required property var barScreen
    required property var barPanel
    property bool autoHide: false
    property bool revealed: true

    /** True while the pointer is over the bar; drives auto-hide. */
    readonly property bool pointerInside: hover.hovered
    /** Held open while a module has a popout showing. */
    property bool holdOpen: false

    readonly property var leftModules: Config.get("bar.left", [])
    readonly property var centreModules: Config.get("bar.center", [])
    readonly property var rightModules: Config.get("bar.right", [])

    GlassSurface {
        id: glass

        anchors.fill: parent
        level: 3
        radius: root.barPanel.floating ? Theme.radiusLg : 0
        padding: 0

        // A bar attached to the edge should not have rounded corners
        // against that edge; the compositor's own edge is straight.
        clipContent: true
    }

    HoverHandler {
        id: hover
    }

    RowLayout {
        id: layout

        anchors.fill: parent
        anchors.leftMargin: Theme.spacingSm
        anchors.rightMargin: Theme.spacingSm
        spacing: 0

        BarSection {
            id: leftSection

            modules: root.leftModules
            hostBar: root
            alignment: Qt.AlignLeft
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredWidth: 1
        }

        BarSection {
            id: centreSection

            modules: root.centreModules
            hostBar: root
            alignment: Qt.AlignHCenter
            Layout.fillHeight: true
            // Its natural width, so the sections either side split what
            // is left and the centre stays centred.
            Layout.preferredWidth: centreSection.implicitWidth
        }

        BarSection {
            id: rightSection

            modules: root.rightModules
            hostBar: root
            alignment: Qt.AlignRight
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredWidth: 1
        }
    }

    // ── Tooltip ────────────────────────────────────────────────────────
    //
    // One tooltip for the whole bar. Modules publish text; this shows it
    // under whichever one the pointer is over.

    readonly property string activeTooltip: {
        const sections = [leftSection, centreSection, rightSection];
        for (const section of sections) {
            const text = section.hoveredTooltip;
            if (text) {
                return text;
            }
        }
        return "";
    }

    readonly property var tooltipAnchor: {
        const sections = [leftSection, centreSection, rightSection];
        for (const section of sections) {
            if (section.hoveredTooltip && section.hoveredItem) {
                return section.hoveredItem;
            }
        }
        return null;
    }

    BarTooltip {
        text: root.activeTooltip
        anchorItem: root.tooltipAnchor
        below: root.barPanel.atTop
        surface: root
    }
}
