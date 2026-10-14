import qs
import qs.modules.common
import qs.modules.common.functions
import qs.modules.common.widgets
import qs.services
import QtQuick
import Quickshell

// Gets the newest Halcyon changes. `update apply` copies only what changed and reloads
// just those parts, so this isn't a full ./setup install. While an update is waiting,
// a few stars drift over the button in the theme's colour.
QuickToggleButton {
    id: root

    readonly property bool updateAvailable: HalcyonUpdates.available

    buttonIcon: HalcyonUpdates.applying ? "downloading" : "system_update"
    toggled: updateAvailable
    onClicked: HalcyonUpdates.apply()

    // The stars: a few small ones, each drifting up and fading in and out at its own pace.
    Repeater {
        model: root.updateAvailable ? 5 : 0

        delegate: MaterialSymbol {
            id: star

            required property int index
            readonly property real startX: 6 + ((index * 37) % 28)
            readonly property real startY: 4 + ((index * 53) % 30)

            text: "star"
            fill: 1
            iconSize: 7 + (index % 3) * 2
            color: Appearance.colors.colPrimary
            x: startX
            y: startY
            opacity: 0

            SequentialAnimation on opacity {
                loops: Animation.Infinite
                PauseAnimation { duration: star.index * 260 }
                NumberAnimation { to: 0.9; duration: 900; easing.type: Easing.InOutSine }
                NumberAnimation { to: 0.1; duration: 900; easing.type: Easing.InOutSine }
            }
            SequentialAnimation on y {
                loops: Animation.Infinite
                NumberAnimation { to: star.startY - 4; duration: 2200 + star.index * 150; easing.type: Easing.InOutSine }
                NumberAnimation { to: star.startY; duration: 2200 + star.index * 150; easing.type: Easing.InOutSine }
            }
            SequentialAnimation on x {
                loops: Animation.Infinite
                NumberAnimation { to: star.startX + 2; duration: 1700; easing.type: Easing.InOutSine }
                NumberAnimation { to: star.startX - 2; duration: 1700; easing.type: Easing.InOutSine }
            }
        }
    }

    StyledToolTip {
        text: HalcyonUpdates.applying ? Translation.tr("Updating Halcyon…")
            : root.updateAvailable ? Translation.tr("Update Halcyon (%1 waiting)").arg(HalcyonUpdates.count)
            : HalcyonUpdates.error !== "" ? Translation.tr("Update Halcyon. Last problem: %1").arg(HalcyonUpdates.error)
            : Translation.tr("Update Halcyon")
    }
}
