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

    // Pressed: the face travels down into the thick bottom border, and the key squashes a little. Animated both
    // ways, so a press and its release are both visible.
    property bool down: false
    property int pressDuration: 70
    // When true, clicking the key presses it.
    property bool interactive: false

    // Presses the key after delayMs and releases it holdMs later. Used to play a chord.
    function tap(delayMs, holdMs) {
        releaseTimer.stop();
        pressTimer.interval = Math.max(1, delayMs);
        releaseTimer.interval = Math.max(1, holdMs);
        pressTimer.restart();
    }

    Timer {
        id: pressTimer
        onTriggered: {
            root.down = true;
            releaseTimer.restart();
        }
    }
    Timer {
        id: releaseTimer
        onTriggered: root.down = false
    }

    implicitWidth: keyFace.implicitWidth + borderWidth * 2
    implicitHeight: keyFace.implicitHeight + borderWidth * 2 + extraBottomBorderWidth
    radius: borderRadius
    color: borderColor
    transformOrigin: Item.Bottom
    scale: down ? 0.96 : 1

    Behavior on scale {
        NumberAnimation {
            duration: root.pressDuration
            easing.type: Easing.OutQuad
        }
    }

    MouseArea {
        anchors.fill: parent
        enabled: root.interactive
        cursorShape: root.interactive ? Qt.PointingHandCursor : Qt.ArrowCursor
        onPressed: root.down = true
        onReleased: root.down = false
        onCanceled: root.down = false
    }

    Rectangle {
        id: keyFace
        anchors {
            fill: parent
            topMargin: borderWidth + (root.down ? extraBottomBorderWidth : 0)
            leftMargin: borderWidth
            rightMargin: borderWidth
            bottomMargin: (root.down ? 0 : extraBottomBorderWidth) + borderWidth
        }
        Behavior on anchors.topMargin {
            NumberAnimation {
                duration: root.pressDuration
                easing.type: Easing.OutQuad
            }
        }
        Behavior on anchors.bottomMargin {
            NumberAnimation {
                duration: root.pressDuration
                easing.type: Easing.OutQuad
            }
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
            width: root.pixelSize
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
