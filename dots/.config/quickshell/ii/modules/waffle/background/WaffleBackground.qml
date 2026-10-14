pragma ComponentBehavior: Bound

import qs
import qs.services
import qs.modules.common
import qs.modules.common.widgets
import qs.modules.common.widgets.widgetCanvas
import QtQuick
import QtQuick.Layouts
import Qt5Compat.GraphicalEffects
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Hyprland

import qs.modules.ii.background.widgets
import qs.modules.ii.background.widgets.clock
import qs.modules.ii.background.widgets.weather
import qs.modules.ii.background.widgets.revolver

Variants {
    id: root
    model: Quickshell.screens

    PanelWindow {
        id: panelRoot
        required property var modelData

        screen: modelData
        exclusionMode: ExclusionMode.Ignore
        WlrLayershell.layer: WlrLayer.Bottom
        WlrLayershell.namespace: "quickshell:background"
        anchors {
            top: true
            bottom: true
            left: true
            right: true
        }
        color: "transparent"

        StyledImage {
            id: wallpaper
            anchors.fill: parent
            source: Config.options.background.wallpaperPath
            fillMode: Image.PreserveAspectCrop
        }

        // Halcyon's revolver, as in the ii family's background. In Red Sun it sits on the wallpaper's red ring: the
        // wallpaper covers the screen, cropped evenly, so a point of the picture lands at scale × it + the offset.
        Item {
            id: halcyonWidgets
            anchors.fill: parent
            readonly property real imageW: wallpaper.implicitWidth
            readonly property real imageH: wallpaper.implicitHeight
            readonly property real coverScale: imageW > 0 && imageH > 0 ? Math.max(width / imageW, height / imageH) : 0
            readonly property real offsetX: (width - imageW * coverScale) / 2
            readonly property real offsetY: (height - imageH * coverScale) / 2
            readonly property bool hasSunRing: ["red-sun", "wallpaper-heaven-kenami"].includes(Config.options.halcyon.theme)
                && /\/(red-sun|wallpaper-heaven-kenami|banner-red-sun)\.jpg$/.test(Config.options.background.wallpaperPath)
                && wallpaper.status === Image.Ready && coverScale > 0

            function wallpaperPoint(u: real, v: real): var {
                return { "x": offsetX + u * imageW * coverScale, "y": offsetY + v * imageH * coverScale };
            }

            RevolverLoader {
                screenWidth: panelRoot.screen.width
                screenHeight: panelRoot.screen.height
                sunRing: {
                    if (!halcyonWidgets.hasSunRing)
                        return null;
                    const p = halcyonWidgets.wallpaperPoint(0.4907, 0.4312);
                    return { "x": p.x, "y": p.y, "r": 0.0369 * halcyonWidgets.imageW * halcyonWidgets.coverScale };
                }
                sunCar: halcyonWidgets.hasSunRing ? halcyonWidgets.wallpaperPoint(0.6485, 0.7084) : null
            }
        }
    }
}
