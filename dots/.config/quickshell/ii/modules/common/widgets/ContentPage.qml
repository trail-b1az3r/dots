import QtQuick
import QtQuick.Layouts
import qs.modules.common
import qs.modules.common.widgets

StyledFlickable {
    id: root
    property real baseWidth: 600
    property bool forceWidth: false
    property real bottomContentPadding: 100

    default property alias contentData: contentColumn.data

    clip: true
    contentHeight: contentColumn.implicitHeight + root.bottomContentPadding // Add some padding at the bottom
    implicitWidth: contentColumn.implicitWidth
    
    ColumnLayout {
        id: contentColumn
        // Never wider than the window: a narrow Settings window wraps the text and the option rows instead of
        // cutting off their right side.
        width: Math.min(root.forceWidth ? root.baseWidth : Math.max(root.baseWidth, implicitWidth), Math.max(280, root.width - 40))
        anchors {
            top: parent.top
            horizontalCenter: parent.horizontalCenter
            margins: 20
        }
        spacing: 30
    }

}
