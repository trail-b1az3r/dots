import QtQuick
import QtQuick.Layouts
import qs.Config
import qs.Components

/** A titled card holding a run of settings. */
ColumnLayout {
    id: root

    property string title: ""
    default property alias rows: card.content

    Layout.fillWidth: true
    spacing: Theme.spacingXs

    Label {
        Layout.fillWidth: true
        Layout.leftMargin: Theme.spacingXs
        visible: root.title.length > 0
        text: root.title
        variant: "caption"
        tone: "tertiary"
        font.weight: Theme.weightSemibold
    }

    GlassSurface {
        id: card
        Layout.fillWidth: true
        level: 1
        radius: Theme.radiusLg
        padding: Theme.panelPadding
        implicitHeight: childrenRect.height + padding * 2
    }
}
