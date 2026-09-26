import QtQuick
import Quickshell
import QtQuick.Layouts
import qs.services
import qs.modules.common
import qs.modules.common.functions
import qs.modules.common.widgets

// Settings > Halcyon: themes, effects and glass.
//
// Everything here is stored under `halcyon` in the shell config, which
// halcyon-theme reads. Changing an effects or glass option re-applies it to
// the active theme through `halcyon-theme refresh`, debounced so dragging a
// slider reloads Hyprland once rather than on every step.
ContentPage {
    id: page
    forceWidth: true

    readonly property string tool: `${FileUtils.trimFileProtocol(Directories.config)}/hypr/hyprland/halcyon/halcyon-theme`
    // Controls report their initial values while the page is being built;
    // only changes made after that are the user's.
    property bool ready: false
    Component.onCompleted: readyTimer.start()

    Timer {
        id: readyTimer
        interval: 300
        onTriggered: page.ready = true
    }

    Timer {
        id: refreshTimer
        // Longer than Config's own write delay, so the file is saved first.
        interval: 700
        onTriggered: Quickshell.execDetached([page.tool, "refresh"])
    }

    function refresh() {
        if (page.ready)
            refreshTimer.restart();
    }

    ContentSection {
        icon: "palette"
        title: Translation.tr("Theme")

        ConfigSelectionArray {
            currentValue: Config.options.halcyon.theme
            onSelected: newValue => {
                Config.options.halcyon.theme = newValue;
                if (newValue === "")
                    Quickshell.execDetached([page.tool, "off"]);
                else
                    Quickshell.execDetached([page.tool, "apply", newValue]);
            }
            options: [
                {
                    displayName: Translation.tr("Wallpaper colours"),
                    icon: "wallpaper",
                    value: ""
                },
                {
                    displayName: "HyperNeo",
                    icon: "desktop_mac",
                    value: "hyperneo"
                },
                {
                    displayName: "Star Rail",
                    icon: "train",
                    value: "hsr"
                },
                {
                    displayName: "Shattered Glass",
                    icon: "broken_image",
                    value: "shattered-glass"
                }
            ]
        }

        StyledText {
            Layout.fillWidth: true
            Layout.leftMargin: 10
            wrapMode: Text.Wrap
            color: Appearance.colors.colSubtext
            font.pixelSize: Appearance.font.pixelSize.smallie
            text: Translation.tr("Applying a theme takes a few seconds. Picking a new wallpaper leaves the theme.\nStar Rail banner art: halcyon banner hsr ~/Pictures/art.png --title \"Name\"")
        }
    }

    ContentSection {
        icon: "auto_awesome"
        title: Translation.tr("Effects")

        ConfigSelectionArray {
            currentValue: Config.options.halcyon.effects
            onSelected: newValue => {
                Config.options.halcyon.effects = newValue;
                page.refresh();
            }
            options: [
                {
                    displayName: Translation.tr("Theme default"),
                    icon: "tune",
                    value: "default"
                },
                {
                    displayName: Translation.tr("Full"),
                    icon: "blur_on",
                    value: "full"
                },
                {
                    displayName: Translation.tr("Light"),
                    icon: "blur_linear",
                    value: "light"
                },
                {
                    displayName: Translation.tr("Off"),
                    icon: "block",
                    value: "off"
                }
            ]
        }

        StyledText {
            Layout.fillWidth: true
            Layout.leftMargin: 10
            wrapMode: Text.Wrap
            color: Appearance.colors.colSubtext
            font.pixelSize: Appearance.font.pixelSize.smallie
            text: Translation.tr("Full adds screen effects that follow the pointer. Hyprland then redraws every frame, which uses noticeably more GPU; Light keeps the glass look without that cost.")
        }
    }

    ContentSection {
        icon: "water_drop"
        title: Translation.tr("Glass")

        ContentSubsection {
            title: Translation.tr("Screen effects")
            tooltip: Translation.tr("Only at the Full effects level, with a theme that has them (Shattered Glass)")

            ConfigRow {
                uniform: true
                ConfigSwitch {
                    buttonIcon: "arrow_selector_tool"
                    text: Translation.tr("Pointer lens")
                    checked: Config.options.halcyon.glass.pointerLens
                    onCheckedChanged: {
                        Config.options.halcyon.glass.pointerLens = checked;
                        page.refresh();
                    }
                }
                ConfigSwitch {
                    buttonIcon: "touch_app"
                    text: Translation.tr("Click ripples")
                    checked: Config.options.halcyon.glass.clickRipples
                    onCheckedChanged: {
                        Config.options.halcyon.glass.clickRipples = checked;
                        page.refresh();
                    }
                }
            }

            ConfigSwitch {
                buttonIcon: "gradient"
                text: Translation.tr("Colour fringe at screen edges")
                checked: Config.options.halcyon.glass.edgeRefraction
                onCheckedChanged: {
                    Config.options.halcyon.glass.edgeRefraction = checked;
                    page.refresh();
                }
            }

            ConfigSlider {
                buttonIcon: "contrast"
                text: Translation.tr("Strength")
                value: Config.options.halcyon.glass.strength
                from: 0
                to: 1
                stopIndicatorValues: [0.5]
                onValueChanged: {
                    Config.options.halcyon.glass.strength = value;
                    page.refresh();
                }
            }

            ConfigSlider {
                buttonIcon: "circle"
                text: Translation.tr("Lens size")
                value: Config.options.halcyon.glass.lensSize
                usePercentTooltip: false
                from: 30
                to: 300
                stopIndicatorValues: [90]
                onValueChanged: {
                    Config.options.halcyon.glass.lensSize = Math.round(value);
                    page.refresh();
                }
            }
        }

        ContentSubsection {
            title: Translation.tr("Glass windows")
            tooltip: Translation.tr("For themes with translucent windows (Shattered Glass), at Light or Full")

            ConfigSlider {
                buttonIcon: "opacity"
                text: Translation.tr("Focused window")
                value: Config.options.halcyon.glass.windowOpacity
                from: 0.5
                to: 1
                stopIndicatorValues: [0.96]
                onValueChanged: {
                    Config.options.halcyon.glass.windowOpacity = value;
                    page.refresh();
                }
            }

            ConfigSlider {
                buttonIcon: "select_window"
                text: Translation.tr("Other windows")
                value: Config.options.halcyon.glass.inactiveWindowOpacity
                from: 0.5
                to: 1
                stopIndicatorValues: [0.9]
                onValueChanged: {
                    Config.options.halcyon.glass.inactiveWindowOpacity = value;
                    page.refresh();
                }
            }

            ConfigSpinBox {
                icon: "blur_on"
                text: Translation.tr("Frost (blur size)")
                value: Config.options.halcyon.glass.blurSize
                from: 1
                to: 30
                stepSize: 1
                onValueChanged: {
                    Config.options.halcyon.glass.blurSize = value;
                    page.refresh();
                }
            }
        }
    }
}
