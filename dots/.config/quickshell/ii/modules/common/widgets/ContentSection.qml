import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.modules.common
import qs.modules.common.widgets

/**
 * A titled block of settings. A click on the title folds it shut, and again opens it; which ones are shut is kept
 * (halcyon.collapsedSections, by title), so a long page stays as short as you left it.
 */
ColumnLayout {
    id: root
    property string title
    property string icon: ""
    /** False keeps a section always open (one with nothing to hide behind its title). */
    property bool collapsible: true
    default property alias contentData: sectionContent.data

    readonly property bool collapsed: collapsible && (Config.options?.halcyon?.collapsedSections ?? []).includes(root.title)

    function toggle() {
        const shut = (Config.options.halcyon.collapsedSections ?? []).filter(t => t !== root.title);
        if (!root.collapsed)
            shut.push(root.title);
        Config.options.halcyon.collapsedSections = shut;
    }

    Layout.fillWidth: true
    spacing: 6

    Item {
        Layout.fillWidth: true
        implicitHeight: header.implicitHeight

        RowLayout {
            id: header
            anchors.fill: parent
            spacing: 6
            OptionalMaterialSymbol {
                icon: root.icon
                iconSize: Appearance.font.pixelSize.hugeass
            }
            StyledText {
                Layout.fillWidth: true
                text: root.title
                font.pixelSize: Appearance.font.pixelSize.larger
                font.weight: Font.Medium
                color: Appearance.colors.colOnSecondaryContainer
            }
            MaterialSymbol {
                visible: root.collapsible
                text: "expand_more"
                iconSize: Appearance.font.pixelSize.hugeass
                color: Appearance.colors.colSubtext
                rotation: root.collapsed ? -90 : 0
                Behavior on rotation {
                    animation: Appearance.animation.elementMoveFast.numberAnimation.createObject(this)
                }
            }
        }

        MouseArea {
            anchors.fill: parent
            enabled: root.collapsible
            cursorShape: Qt.PointingHandCursor
            onClicked: root.toggle()
        }
    }

    ColumnLayout {
        id: sectionContent
        Layout.fillWidth: true
        spacing: 4
        visible: !root.collapsed
        opacity: root.collapsed ? 0 : 1
        Behavior on opacity {
            animation: Appearance.animation.elementMoveFast.numberAnimation.createObject(this)
        }
    }
}
