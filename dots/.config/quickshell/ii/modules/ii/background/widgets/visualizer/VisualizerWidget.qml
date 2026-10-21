import QtQuick
import qs
import qs.services
import qs.modules.common
import qs.modules.common.widgets
import qs.modules.ii.background.widgets

/**
 * The audio visualizer on the desktop: the spectrum of what is playing, in the theme's colours. Settings >
 * Background > Widget: Audio visualizer picks the style (bars, mirror, wave, ring), the size, whether it sits on a
 * card in the theme's shape, and whether it is a window on the screen-edge strip instead (VisualizerWindow).
 */
AbstractBackgroundWidget {
    id: root

    configEntryName: "visualizer"

    readonly property var settings: Config.options.background.widgets.visualizer

    implicitWidth: Math.max(120, settings.width)
    implicitHeight: Math.max(60, settings.height)

    // cava runs while this is on screen, and only then.
    SpectrumUse {
        wanted: root.visible
    }
    Binding {
        target: AudioSpectrum
        property: "bars"
        value: Math.max(8, Math.min(128, root.settings.bars))
    }
    Binding {
        target: AudioSpectrum
        property: "framerate"
        value: Math.max(10, Math.min(60, root.settings.fps))
    }

    // Resting when nothing plays, if asked.
    opacity: (GlobalStates.screenLocked && !visibleWhenLocked) ? 0
        : ((settings.hideWhenSilent && AudioSpectrum.silent) ? 0 : 1)

    ThemedPlate {
        anchors.fill: parent
        visible: root.settings.panel
        themeId: Config.options.halcyon.theme
        kind: "card"
        colBase: Appearance.colors.colLayer1
        colOn: Appearance.colors.colOnLayer1
        colAccent: Appearance.colors.colPrimary
    }

    SpectrumView {
        anchors.fill: parent
        anchors.margins: root.settings.panel ? 22 : 0
        points: AudioSpectrum.points
        style: root.settings.style
        barCount: Math.max(8, Math.min(128, root.settings.bars))
        live: !AudioSpectrum.silent
    }
}
