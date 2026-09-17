import QtQuick
import qs.Config

/** A square icon-only button, for toolbars and panel headers. */
Item {
    id: root

    property string glyph: ""
    property string icon: ""
    property string tooltip: ""
    property bool enabled: true
    property bool active: false
    property int size: 32
    property int iconSize: Theme.sizeBodyLarge

    signal clicked
    signal rightClicked

    implicitWidth: root.size
    implicitHeight: root.size
    opacity: root.enabled ? 1.0 : 0.4

    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusSm
        color: root.active ? Theme.surfaceSelected : "transparent"
        border.width: root.active ? 1 : 0
        border.color: Theme.accent

        Behavior on color {
            enabled: Theme.animationsEnabled
            ColorAnimation { duration: Theme.durInstant }
        }
    }

    Icon {
        anchors.centerIn: parent
        source: root.icon
        glyph: root.glyph
        size: root.iconSize
        color: root.active ? Theme.accentText : Theme.text
    }

    StateLayer {
        anchors.fill: parent
        radius: Theme.radiusSm
        enabled: root.enabled
        focusVisible: root.activeFocus
        onClicked: root.clicked()
        onRightClicked: root.rightClicked()
    }

    Accessible.role: Accessible.Button
    Accessible.name: root.tooltip.length > 0 ? root.tooltip : root.glyph
    Accessible.onPressAction: root.clicked()
}
