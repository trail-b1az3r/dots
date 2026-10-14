import QtQuick
import Quickshell
import qs
import qs.services
import qs.modules.common
import qs.modules.waffle.looks
import qs.modules.waffle.bar.tray

BarIconButton {
    id: root

    // Halcyon's own updates (HalcyonUpdates) light it too; a click then updates Halcyon first.
    readonly property bool halcyon: HalcyonUpdates.available || HalcyonUpdates.applying
    visible: root.halcyon || Updates.updateAdvised || Updates.updateStronglyAdvised
    padding: 4
    iconName: "arrow-sync"
    iconSize: 20 // Needed because the icon appears to have some padding
    iconMonochrome: true
    tooltipText: root.halcyon
        ? (HalcyonUpdates.applying ? Translation.tr("Updating Halcyon…") : Translation.tr("Halcyon update: %1 new on main. Click to update.").arg(HalcyonUpdates.count))
        : Translation.tr("Get the latest features and security improvements with\nthe newest feature update.\n\n%1 packages").arg(Updates.count)

    onClicked: {
        if (root.halcyon)
            HalcyonUpdates.apply();
        else
            Quickshell.execDetached(["bash", "-c", Config.options.apps.update]);
    }

    overlayingItems: Rectangle {
        anchors {
            right: parent.right
            bottom: parent.bottom
            margins: 1
        }
        implicitWidth: 8
        implicitHeight: implicitWidth
        radius: height / 2
        color: (!root.halcyon && Updates.updateStronglyAdvised) ? Looks.colors.warning : Looks.colors.accent
    }
}
