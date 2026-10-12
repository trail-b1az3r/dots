import qs.modules.common
import qs.modules.common.widgets
import qs.modules.common.models.quickToggles
import QtQuick

// The Android-style update button, with a few stars drifting over it in the theme's colour while
// an update waits. Each star drifts up and fades at its own pace.
AndroidQuickToggleButton {
    toggleModel: HalcyonUpdateToggle {}

    Repeater {
        model: toggleModel?.updateAvailable ? 5 : 0

        delegate: MaterialSymbol {
            id: star

            required property int index
            readonly property real startX: (star.parent?.width ?? 0) * (0.12 + 0.17 * index)
            readonly property real startY: (star.parent?.height ?? 0) * (0.18 + 0.14 * (index % 3))

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
        }
    }
}
