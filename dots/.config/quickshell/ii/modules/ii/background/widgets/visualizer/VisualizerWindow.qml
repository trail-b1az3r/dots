import QtQuick
import Quickshell
import qs
import qs.services
import qs.modules.common
import qs.modules.common.functions

/**
 * The audio visualizer as a window (Settings > Background > Widget: Audio visualizer > "As a window"). With
 * hyprland-plus the superposition rule on its title keeps it tiled on the screen-edge strip, drawn above fullscreen
 * windows too, so the music shows over a game or a video. On stock Hyprland it is an ordinary window.
 *
 * Closing the window turns the widget off.
 */
FloatingWindow {
    id: win

    // hyprland/halcyon/app_rules.lua matches this title.
    title: "Halcyon Visualizer"
    color: "transparent"
    implicitWidth: 360
    implicitHeight: 170
    visible: true

    readonly property var settings: Config.options.background.widgets.visualizer

    onVisibleChanged: {
        if (!visible)
            Config.options.background.widgets.visualizer.enable = false;
    }

    SpectrumUse {
        wanted: win.visible
    }
    Binding {
        target: AudioSpectrum
        property: "bars"
        value: Math.max(8, Math.min(64, win.settings.bars))
    }
    Binding {
        target: AudioSpectrum
        property: "framerate"
        value: Math.max(10, Math.min(60, win.settings.fps))
    }

    Rectangle {
        anchors.fill: parent
        radius: Appearance.rounding.normal
        color: ColorUtils.transparentize(Appearance.colors.colLayer0, 0.18)
        border.width: 1
        border.color: Appearance.colors.colLayer0Border

        SpectrumView {
            anchors.fill: parent
            anchors.margins: 16
            points: AudioSpectrum.points
            style: win.settings.style
            barCount: Math.max(8, Math.min(64, win.settings.bars))
            live: !AudioSpectrum.silent
        }
    }
}
