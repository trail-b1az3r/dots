import QtQuick
import QtQuick.Layouts
import qs.Config

/**
 * One of the bar's three sections: a row of modules, by id.
 *
 * A module id that is repeated in a section is instantiated twice, which
 * is intended — two spacers, or two separators, are a reasonable layout.
 * An id nobody recognises becomes a visible marker rather than nothing,
 * so a typo in settings is a thing you can see.
 */
Item {
    id: root

    required property var modules
    required property var hostBar
    property int alignment: Qt.AlignLeft

    /** Tooltip text of whichever module the pointer is over, if any. */
    readonly property string hoveredTooltip: {
        for (let index = 0; index < repeater.count; index++) {
            const host = repeater.itemAt(index);
            if (host && host.tooltip) {
                return host.tooltip;
            }
        }
        return "";
    }

    readonly property var hoveredItem: {
        for (let index = 0; index < repeater.count; index++) {
            const host = repeater.itemAt(index);
            if (host && host.tooltip) {
                return host;
            }
        }
        return null;
    }

    implicitWidth: row.implicitWidth
    implicitHeight: parent ? parent.height : 0

    Row {
        id: row

        height: parent.height
        spacing: Theme.spacingXxs

        anchors.left: root.alignment === Qt.AlignLeft ? parent.left : undefined
        anchors.right: root.alignment === Qt.AlignRight ? parent.right : undefined
        anchors.horizontalCenter: root.alignment === Qt.AlignHCenter
            ? parent.horizontalCenter : undefined

        Repeater {
            id: repeater

            model: root.modules

            delegate: BarModuleHost {
                required property string modelData

                moduleId: modelData
                bar: root.hostBar
                height: row.height
            }
        }
    }
}
