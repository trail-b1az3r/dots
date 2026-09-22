import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.Config
import qs.Services

/**
 * Halcyon Ultra Bar — one bar per monitor, driven from settings.
 *
 * `Variants` over `Quickshell.screens` is what makes multi-monitor work
 * rather than being claimed: monitors appearing and disappearing add and
 * remove bars, and each bar's modules are bound to its own screen, so a
 * workspace indicator shows that monitor's workspaces.
 *
 * The layout is three lists of module ids in settings. This file never
 * names a module; it asks BarModuleHost to load ids. Adding a module to
 * the bar is an edit to settings.json, not to QML.
 *
 * Exclusion is deliberate: a floating bar still reserves its own height
 * so windows do not slide underneath it, but an auto-hiding bar reserves
 * nothing, because reserving space for something you cannot see is the
 * worst of both.
 */
Variants {
    id: root

    model: Quickshell.screens

    delegate: Component {
        PanelWindow {
            id: panel

            required property var modelData
            readonly property var screenData: panel.modelData

            // One bar, or one per monitor.
            readonly property bool wanted: {
                if (!Config.get("bar.enabled", true)) {
                    return false;
                }
                if (Config.get("bar.showOnAllMonitors", true)) {
                    return true;
                }
                // Primary only: Quickshell has no "primary" flag, so the
                // first screen Wayland reports stands in for it.
                return Quickshell.screens.length === 0
                    || Quickshell.screens[0] === panel.screenData;
            }

            readonly property bool atTop: Config.get("bar.position", "top") === "top"
            readonly property bool floating: Config.get("bar.floating", true)
            readonly property bool autoHide: Config.get("bar.autoHide", false)
            readonly property int barHeight: Math.max(
                18, Config.get("bar.height", 34))
            readonly property int sideMargin: panel.floating
                ? Config.get("bar.sideMargin", 10) : 0
            readonly property int edgeMargin: panel.floating
                ? Config.get("bar.topMargin", 6) : 0

            // The strip left on screen when hidden: enough to aim at.
            readonly property int peek: 2
            readonly property bool revealed: !panel.autoHide
                || surface.pointerInside || surface.holdOpen

            screen: panel.screenData
            visible: panel.wanted
            color: "transparent"

            WlrLayershell.namespace: "halcyon-bar"
            WlrLayershell.layer: WlrLayer.Top
            WlrLayershell.keyboardFocus: WlrKeyboardFocus.None

            anchors {
                top: panel.atTop
                bottom: !panel.atTop
                left: true
                right: true
            }

            margins {
                top: panel.atTop ? panel.edgeMargin : 0
                bottom: panel.atTop ? 0 : panel.edgeMargin
                left: panel.sideMargin
                right: panel.sideMargin
            }

            implicitHeight: panel.barHeight + panel.edgeMargin

            // An auto-hiding bar reserves nothing; a visible one reserves
            // exactly what it occupies, margins included.
            exclusionMode: panel.autoHide ? ExclusionMode.Ignore
                : ExclusionMode.Auto
            exclusiveZone: panel.autoHide ? 0
                : panel.barHeight + panel.edgeMargin

            BarSurface {
                id: surface

                anchors.left: parent.left
                anchors.right: parent.right
                height: panel.barHeight
                barScreen: panel.screenData
                barPanel: panel
                autoHide: panel.autoHide
                revealed: panel.revealed

                y: {
                    if (panel.revealed) {
                        return panel.atTop ? panel.edgeMargin : 0;
                    }
                    // Slide out of view, leaving a sliver to hover.
                    return panel.atTop
                        ? -(panel.barHeight - panel.peek)
                        : panel.barHeight - panel.peek;
                }

                Behavior on y {
                    enabled: Theme.animationsEnabled
                    NumberAnimation {
                        duration: Theme.durStandard
                        easing.type: Easing.Bezier
                        easing.bezierCurve: Theme.curve("emphasised")
                    }
                }
            }
        }
    }
}
