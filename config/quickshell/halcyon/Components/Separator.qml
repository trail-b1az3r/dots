import QtQuick
import qs.Config

/**
 * A hairline rule.
 *
 * Sizing is left to the caller — inside a Layout it wants `Layout.fillWidth`,
 * and inside an anchored column it wants anchors. Setting attached Layout
 * properties here would warn everywhere it is used outside a layout.
 */
Rectangle {
    property bool vertical: false

    implicitWidth: vertical ? 1 : 120
    implicitHeight: vertical ? 120 : 1
    color: Theme.separator
}
