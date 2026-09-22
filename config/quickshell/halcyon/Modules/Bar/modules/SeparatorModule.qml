import QtQuick
import qs.Config

/** A hairline between groups of modules. */
Item {
    id: root

    property string tooltip: ""
    property var hostBar: null

    implicitWidth: Theme.spacingSm * 2 + 1
    implicitHeight: parent ? parent.height : 0

    Rectangle {
        anchors.centerIn: parent
        width: 1
        height: Math.max(10, parent.height - Theme.spacingMd * 2)
        color: Qt.rgba(Theme.text.r, Theme.text.g, Theme.text.b, 0.14)
    }
}
