import QtQuick
import qs.common

// A side menu page's top: back, its name, and whatever goes on the right (a switch, a button).
Item {
    id: root
    property string title
    default property alias end: endRow.data
    signal back
    implicitHeight: 40

    BarButton {
        id: backButton
        anchors.verticalCenter: parent.verticalCenter
        icon: "arrow_back"
        implicitHeight: 34
        onClicked: root.back()
    }
    Text {
        anchors.left: backButton.right
        anchors.leftMargin: 8
        anchors.verticalCenter: parent.verticalCenter
        text: root.title
        color: Theme.text
        font.family: Theme.font
        font.pixelSize: 17
        font.weight: Font.DemiBold
    }
    Row {
        id: endRow
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        spacing: 4
    }
}
