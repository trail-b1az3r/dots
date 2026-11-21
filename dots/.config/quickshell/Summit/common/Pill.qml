import QtQuick
import qs.common

// A group on a bar: a soft rounded slab of the theme's surface, a hairline edge, its children in a row.
Rectangle {
    id: root
    default property alias content: row.data
    property int padding: 6
    property alias spacing: row.spacing
    implicitWidth: row.implicitWidth + padding * 2
    implicitHeight: Theme.barHeight
    radius: Theme.radius
    color: Theme.alpha(Theme.surface, Theme.barOpacity)
    border.width: 1
    border.color: Theme.alpha(Theme.outline, 0.07)

    Row {
        id: row
        anchors.verticalCenter: parent.verticalCenter
        x: root.padding
        spacing: 2
    }
}
