import qs.modules.common
import qs.modules.common.widgets
import QtQuick
import QtQuick.Layouts

// One theme in Settings > Halcyon. A left click applies it. A right click
// drops its menu down underneath the row.
ColumnLayout {
    id: root

    property string themeId
    property string label
    property string icon
    property bool isActive: false
    property bool menuOpen: false
    // Each item is { key, text, icon }. Empty for a row with no menu.
    property var menuItems: []

    signal applied()
    signal menuToggled()
    signal itemChosen(string key)

    Layout.fillWidth: true
    spacing: 2

    RippleButton {
        Layout.fillWidth: true
        implicitHeight: 44
        buttonRadius: Appearance.rounding.normal
        toggled: root.isActive
        onClicked: root.applied()
        altAction: () => {
            if (root.menuItems.length > 0)
                root.menuToggled();
        }

        contentItem: RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 14
            anchors.rightMargin: 14
            spacing: 10

            MaterialSymbol {
                text: root.icon
                iconSize: Appearance.font.pixelSize.larger
                color: root.isActive ? Appearance.colors.colOnPrimary : Appearance.colors.colOnLayer1
            }

            StyledText {
                Layout.fillWidth: true
                text: root.label
                font.pixelSize: Appearance.font.pixelSize.small
                color: root.isActive ? Appearance.colors.colOnPrimary : Appearance.colors.colOnLayer1
            }

            MaterialSymbol {
                visible: root.menuItems.length > 0
                text: root.menuOpen ? "expand_less" : "expand_more"
                iconSize: Appearance.font.pixelSize.larger
                color: root.isActive ? Appearance.colors.colOnPrimary : Appearance.colors.colOnLayer1
            }
        }
    }

    Revealer {
        Layout.fillWidth: true
        reveal: root.menuOpen
        vertical: true

        ColumnLayout {
            width: parent.width
            spacing: 2

            Repeater {
                model: root.menuItems

                delegate: RippleButton {
                    required property var modelData

                    Layout.fillWidth: true
                    implicitHeight: 38
                    buttonRadius: Appearance.rounding.small
                    onClicked: root.itemChosen(modelData.key)

                    contentItem: RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 28
                        anchors.rightMargin: 14
                        spacing: 10

                        MaterialSymbol {
                            text: modelData.icon
                            iconSize: Appearance.font.pixelSize.normal
                            color: Appearance.colors.colOnLayer1
                        }

                        StyledText {
                            Layout.fillWidth: true
                            text: modelData.text
                            font.pixelSize: Appearance.font.pixelSize.small
                            color: Appearance.colors.colOnLayer1
                        }
                    }
                }
            }
        }
    }
}
