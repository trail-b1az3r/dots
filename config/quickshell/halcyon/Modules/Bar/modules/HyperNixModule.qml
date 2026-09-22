import QtQuick
import qs.Config
import qs.Services
import qs.Components
import "../"

/**
 * HyperNix state.
 *
 * Hidden when HyperNix is not installed or the integration is off, so
 * the bar carries nothing for a tool the machine does not have.
 */
BarItem {
    id: root

    property var hostBar: null

    visible: HyperNix.available
    tooltip: HyperNix.summary || qsTr("HyperNix %1").arg(HyperNix.version)
    onActivated: HyperNix.launch()
    onSecondaryActivated: HyperNix.refresh()

    content: Row {
        spacing: Theme.spacingXs

        Icon {
            anchors.verticalCenter: parent.verticalCenter
            glyph: "\udb84\udc8d"
            size: Theme.sizeBody
            color: Theme.textSecondary
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            visible: HyperNix.version !== ""
            text: HyperNix.version
            color: Theme.textSecondary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeCaption
            renderType: Text.QtRendering
        }
    }
}
