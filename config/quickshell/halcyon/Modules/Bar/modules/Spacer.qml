import QtQuick
import qs.Config

/** A flexible gap. Two of these push a module to the far edge. */
Item {
    id: root

    property string tooltip: ""
    property var hostBar: null

    implicitWidth: Theme.spacingXl
    implicitHeight: parent ? parent.height : 0
}
