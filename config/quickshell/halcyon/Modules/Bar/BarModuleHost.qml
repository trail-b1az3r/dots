import QtQuick
import qs.Config
import qs.Components

/**
 * One bar module, loaded by id, isolated from the rest.
 *
 * The bar is a row of independent things, and a mistake in any one of
 * them must not empty the row. A module that fails to load leaves a
 * small marker in its place rather than taking the bar down — visible,
 * because a silently missing module is a bug nobody reports, but narrow
 * enough not to wreck the layout.
 *
 * Modules are addressed by id so the layout can live in settings as
 * three lists of strings. `BarModules.source(id)` maps the id to a file;
 * an id with no mapping is reported the same way as one that failed.
 */
Item {
    id: root

    required property string moduleId
    /** Passed through to the module as `hostBar`, for popouts. */
    property var bar: null

    readonly property string sourceFile: BarModules.source(root.moduleId)
    readonly property bool known: root.sourceFile !== ""
    readonly property bool failed: loader.status === Loader.Error || !root.known
    readonly property string failureText: {
        if (!root.known) {
            return qsTr("unknown module: %1").arg(root.moduleId);
        }
        if (loader.status === Loader.Error) {
            return qsTr("%1 failed to load").arg(root.moduleId);
        }
        return "";
    }

    implicitWidth: root.failed ? marker.implicitWidth
        : (loader.item ? loader.item.implicitWidth : 0)
    implicitHeight: parent ? parent.height : 0
    visible: root.failed || (loader.item ? loader.item.visible : false)

    Loader {
        id: loader

        anchors.fill: parent
        active: root.known
        asynchronous: false
        source: root.sourceFile

        onStatusChanged: {
            if (loader.status === Loader.Error) {
                console.warn("halcyon: bar module", root.moduleId,
                             "failed to load:", loader.sourceComponent
                                 ? loader.sourceComponent.errorString() : "");
            }
        }

        onLoaded: {
            if (loader.item && loader.item.hasOwnProperty("hostBar")) {
                loader.item.hostBar = root.bar;
            }
        }
    }

    // The placeholder for a broken module. Deliberately plain: it is a
    // diagnostic, not a design element.
    Rectangle {
        id: marker

        anchors.centerIn: parent
        visible: root.failed
        implicitWidth: Math.max(16, label.implicitWidth + Theme.spacingSm * 2)
        implicitHeight: 16
        radius: 4
        color: Qt.rgba(Theme.danger.r, Theme.danger.g, Theme.danger.b, 0.18)
        border.width: 1
        border.color: Qt.rgba(Theme.danger.r, Theme.danger.g, Theme.danger.b, 0.5)

        Text {
            id: label

            anchors.centerIn: parent
            text: "!"
            color: Theme.danger
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeCaption
            font.bold: true
        }

        HoverHandler {
            id: markerHover
        }
    }

    // The bar owns one tooltip and modules feed it, rather than every
    // module carrying its own popup window.
    readonly property string tooltip: markerHover.hovered ? root.failureText
        : (loader.item && loader.item.hasOwnProperty("tooltip")
            ? loader.item.tooltip : "")
}
