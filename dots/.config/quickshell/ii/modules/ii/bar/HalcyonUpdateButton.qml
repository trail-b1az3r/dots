import qs.services
import qs.modules.common
import qs.modules.common.widgets
import QtQuick
import QtQuick.Layouts

/**
 * Shown in the bar while a Halcyon update is waiting (or one is being applied, or the last one failed). A click
 * updates: `update apply` copies only what changed and reloads just that. The sidebar's Update Halcyon button does
 * the same.
 */
RippleButton {
    id: root

    readonly property bool failed: !HalcyonUpdates.available && !HalcyonUpdates.applying && HalcyonUpdates.error !== ""
    visible: HalcyonUpdates.available || HalcyonUpdates.applying || root.failed

    implicitHeight: 28
    implicitWidth: row.implicitWidth + 10 * 2
    buttonRadius: Appearance.rounding.full
    colBackground: root.failed ? Appearance.colors.colErrorContainer : Appearance.colors.colPrimaryContainer
    colBackgroundHover: root.failed ? Appearance.colors.colErrorContainerHover : Appearance.colors.colPrimaryContainerHover
    colRipple: root.failed ? Appearance.colors.colErrorContainerActive : Appearance.colors.colPrimaryContainerActive
    onClicked: HalcyonUpdates.apply()

    RowLayout {
        id: row
        anchors.centerIn: parent
        spacing: 4

        MaterialSymbol {
            text: HalcyonUpdates.applying ? "sync" : root.failed ? "sync_problem" : "system_update"
            iconSize: Appearance.font.pixelSize.large
            color: root.failed ? Appearance.colors.colOnErrorContainer : Appearance.colors.colOnPrimaryContainer
            RotationAnimation on rotation {
                running: HalcyonUpdates.applying
                loops: Animation.Infinite
                from: 360
                to: 0
                duration: 1200
            }
            onTextChanged: rotation = 0
        }
        StyledText {
            visible: HalcyonUpdates.available && !HalcyonUpdates.applying
            text: HalcyonUpdates.count
            font.pixelSize: Appearance.font.pixelSize.small
            color: Appearance.colors.colOnPrimaryContainer
        }
    }

    StyledToolTip {
        text: HalcyonUpdates.applying ? Translation.tr("Updating Halcyon…")
            : root.failed ? Translation.tr("The last Halcyon update failed: %1\nClick to try again.").arg(HalcyonUpdates.error)
            : Translation.tr("Halcyon update: %1 new on main. Click to update.").arg(HalcyonUpdates.count)
    }
}
