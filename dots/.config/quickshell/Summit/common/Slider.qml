import QtQuick
import qs.common

// The Halcyon shell's quick slider (its StyledSlider, "M" size), in Summit's colours: a thick track, filled in the
// accent up to a slim handle with a gap either side, the icon inside the track at its end (on the fill once the fill
// reaches it), and optionally a second icon marking a point on the track (the brightness slider's sun, where the
// backlight ends and the dimming begins). Drag, click or scroll; the value shows above the handle while it moves.
Item {
    id: root
    property real value: 0          // 0..1
    property string icon: ""
    property string markIcon: ""
    property real markAt: 0.3
    property string valueText: Math.round(root.value * 100) + "%"
    signal moved(real value)

    implicitHeight: 40
    implicitWidth: 260

    readonly property real handleWidth: 4
    readonly property real gapWidth: 5
    readonly property real usable: width - handleWidth - gapWidth * 2
    readonly property real handleX: gapWidth + value * usable
    readonly property bool dragging: area.pressed

    function setFrom(x) {
        root.moved(Math.max(0, Math.min(1, (x - root.gapWidth - root.handleWidth / 2) / root.usable)));
    }

    // The empty track, then the fill over it.
    Rectangle {
        x: root.handleX + root.handleWidth + root.gapWidth
        width: Math.max(0, root.width - x)
        height: parent.height
        radius: 12
        color: Theme.alpha(Theme.text, 0.12)
        // Square on the handle's side.
        Rectangle { width: Math.min(parent.width, 12); height: parent.height; color: parent.color; visible: parent.width > 12 }
    }
    Rectangle {
        width: Math.max(0, root.handleX - root.gapWidth)
        height: parent.height
        radius: 12
        color: Theme.accent
        Rectangle { anchors.right: parent.right; width: Math.min(parent.width, 12); height: parent.height; color: parent.color; visible: parent.width > 12 }
    }
    // The handle: a slim bar, a little taller than the track.
    Rectangle {
        x: root.handleX
        y: -3
        width: root.handleWidth
        height: parent.height + 6
        radius: 2
        color: Theme.accent
        scale: root.dragging ? 1.12 : 1
        Behavior on scale { NumberAnimation { duration: Theme.animMs; easing.type: Easing.OutBack } }
    }

    // The mark: a stop on the track, drawn on whichever part it is in.
    Symbol {
        visible: root.markIcon !== ""
        name: root.markIcon
        size: 18
        readonly property real at: root.gapWidth + root.markAt * root.usable
        readonly property bool near: Math.abs(at - root.handleX) < 22
        x: near ? root.handleX - width - 8 : at - width / 2
        anchors.verticalCenter: parent.verticalCenter
        color: root.value >= root.markAt ? Theme.accentText : Theme.alpha(Theme.text, 0.7)
        Behavior on color { ColorAnimation { duration: Theme.animMs } }
        Behavior on x { NumberAnimation { duration: Theme.animMs; easing.type: Easing.OutCubic } }
    }
    // The icon at the end; on the fill, beside the handle, once the fill gets there.
    Symbol {
        id: endIcon
        visible: root.icon !== ""
        name: root.icon
        size: 20
        fill: 1
        readonly property bool onFill: root.value >= 0.88
        x: onFill ? root.handleX - width - 10 : root.width - width - 10
        anchors.verticalCenter: parent.verticalCenter
        color: onFill ? Theme.accentText : Theme.text
        Behavior on color { ColorAnimation { duration: Theme.animMs } }
        Behavior on x { NumberAnimation { duration: Theme.animMs; easing.type: Easing.OutCubic } }
    }

    // The value, over the handle while it is dragged or scrolled.
    Rectangle {
        id: bubble
        property bool shown: root.dragging || bubbleTimer.running
        opacity: shown ? 1 : 0
        scale: shown ? 1 : 0.7
        Behavior on opacity { NumberAnimation { duration: Theme.animMs } }
        Behavior on scale { NumberAnimation { duration: Theme.animMs; easing.type: Easing.OutBack } }
        x: Math.max(0, Math.min(root.width - width, root.handleX + root.handleWidth / 2 - width / 2))
        y: -height - 8
        width: bubbleText.implicitWidth + 16
        height: 24
        radius: 12
        color: Theme.surfaceHigh
        Text {
            id: bubbleText
            anchors.centerIn: parent
            text: root.valueText
            color: Theme.text
            font.family: Theme.font
            font.pixelSize: 12
            font.weight: Font.DemiBold
        }
    }
    Timer {
        id: bubbleTimer
        interval: 900
    }

    MouseArea {
        id: area
        anchors.fill: parent
        anchors.topMargin: -4
        anchors.bottomMargin: -4
        cursorShape: Qt.PointingHandCursor
        onPressed: mouse => root.setFrom(mouse.x)
        onPositionChanged: mouse => { if (pressed) root.setFrom(mouse.x); }
        onWheel: wheel => {
            root.moved(Math.max(0, Math.min(1, root.value + (wheel.angleDelta.y > 0 ? 0.05 : -0.05))));
            bubbleTimer.restart();
        }
    }
}
