import QtQuick
import Quickshell
import qs
import qs.services
import qs.modules.common

// Gets the newest Halcyon changes: `update apply` copies only what changed and reloads
// just those parts. Lit while updates are waiting (HalcyonUpdates).
QuickToggleModel {
    id: model

    name: Translation.tr("Update Halcyon")
    hasStatusText: false
    icon: HalcyonUpdates.applying ? "downloading" : "system_update"
    readonly property bool updateAvailable: HalcyonUpdates.available
    toggled: updateAvailable

    mainAction: () => HalcyonUpdates.apply()

    tooltipText: HalcyonUpdates.applying ? Translation.tr("Updating Halcyon…")
        : updateAvailable ? Translation.tr("Update Halcyon (%1 waiting)").arg(HalcyonUpdates.count)
        : HalcyonUpdates.error !== "" ? Translation.tr("Update Halcyon. Last problem: %1").arg(HalcyonUpdates.error)
        : Translation.tr("Update Halcyon")
}
