import qs.modules.common
import QtQuick

Rectangle {
    id: root
    property string key

    property real horizontalPadding: 6
    property real verticalPadding: 1
    property real borderWidth: 1
    property real extraBottomBorderWidth: 2
    property color borderColor: Appearance.colors.colOnLayer0
    property real borderRadius: 5
    property real pixelSize: Appearance.font.pixelSize.smaller
    property color keyColor: Appearance.m3colors.m3surfaceContainerLow
    implicitWidth: keyFace.implicitWidth + borderWidth * 2
    implicitHeight: keyFace.implicitHeight + borderWidth * 2 + extraBottomBorderWidth
    radius: borderRadius
    color: borderColor

    Rectangle {
        id: keyFace
        anchors {
            fill: parent
            topMargin: borderWidth
            leftMargin: borderWidth
            rightMargin: borderWidth
            bottomMargin: extraBottomBorderWidth + borderWidth
        }
        // "halcyon" stands for the Halcyon mark, which the Super key can be set to.
        readonly property bool isLogo: root.key === "halcyon"
        implicitWidth: (isLogo ? logo.width : keyText.implicitWidth) + horizontalPadding * 2
        implicitHeight: (isLogo ? logo.height : keyText.implicitHeight) + verticalPadding * 2
        color: keyColor
        radius: borderRadius - borderWidth

        StyledText {
            id: keyText
            anchors.centerIn: parent
            visible: !keyFace.isLogo
            font.family: Appearance.font.family.monospace
            font.pixelSize: root.pixelSize
            text: key
        }

        // The Halcyon mark, drawn in the key's text colour so it matches the other symbols.
        Item {
            id: logo
            anchors.centerIn: parent
            visible: keyFace.isLogo
            width: root.pixelSize * 1.2
            height: width

            Rectangle {
                anchors.fill: parent
                color: Appearance.m3colors.m3onBackground
                layer.enabled: true
                layer.effect: MaskMultiEffect {
                    maskSource: logoImage
                }
            }

            Image {
                id: logoImage
                anchors.fill: parent
                visible: false
                sourceSize.width: width
                sourceSize.height: height
                fillMode: Image.PreserveAspectFit
                source: Qt.resolvedUrl("../../../assets/icons/halcyon-key.svg")
            }
        }
    }
}
