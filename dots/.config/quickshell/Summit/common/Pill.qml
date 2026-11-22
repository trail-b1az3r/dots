import QtQuick
import qs.common

// A group on a bar: a pane of frosted glass, its children in a row.
Glass {
    id: root
    default property alias content: row.data
    property int padding: 6
    property alias spacing: row.spacing
    implicitWidth: row.implicitWidth + padding * 2
    implicitHeight: Theme.barHeight
    radius: Theme.radius

    Row {
        id: row
        anchors.verticalCenter: parent.verticalCenter
        x: root.padding
        spacing: 2
    }
}
