import QtQuick
import Quickshell
import QtQuick.Layouts
import qs.services
import qs.modules.common
import qs.modules.common.functions
import qs.modules.common.widgets

// Settings > Revolver: the drum of installed games on the desktop.
//
// Off by default. The games are read from local files by halcyon-theme, and
// the widget is drawn on the background. Turning it on loads it straight away.
ContentPage {
    id: page
    forceWidth: true

    ContentSection {
        icon: "casino"
        title: Translation.tr("Revolver")

        ConfigSwitch {
            buttonIcon: "casino"
            text: Translation.tr("Show the revolver on the desktop")
            checked: Config.options.background.widgets.revolver.enable
            onCheckedChanged: Config.options.background.widgets.revolver.enable = checked
            StyledToolTip {
                text: Translation.tr("A drum of your installed games, drawn in the theme's shapes. Flick it to spin: the game that stops under the hammer starts. A slow nudge only turns it.")
            }
        }

        ConfigSwitch {
            buttonIcon: "radio_button_unchecked"
            text: Translation.tr("In Red Sun, sit on the wallpaper's red ring")
            checked: Config.options.background.widgets.revolver.followRing
            onCheckedChanged: Config.options.background.widgets.revolver.followRing = checked
            StyledToolTip {
                text: Translation.tr("The ring is the drum: it lights up as it turns, and at the Full effects level a spin breaks the screen")
            }
        }

        ContentSubsection {
            title: Translation.tr("Games come from")
            ConfigSelectionArray {
                currentValue: Config.options.background.widgets.revolver.source
                onSelected: newValue => Config.options.background.widgets.revolver.source = newValue
                options: [
                    { displayName: "Steam", value: "steam" },
                    { displayName: "PrismLauncher", value: "prismlauncher" }
                ]
            }
        }

        ContentSubsection {
            title: Translation.tr("Weighting")
            ConfigSelectionArray {
                currentValue: Config.options.background.widgets.revolver.mode
                onSelected: newValue => Config.options.background.widgets.revolver.mode = newValue
                options: [
                    { displayName: Translation.tr("Recent"), value: "recent" },
                    { displayName: Translation.tr("Random"), value: "random" },
                    { displayName: Translation.tr("Recommended"), value: "recommended" }
                ]
            }
        }

        ContentSubsection {
            title: Translation.tr("Size")
            ConfigSelectionArray {
                currentValue: Config.options.background.widgets.revolver.size
                onSelected: newValue => Config.options.background.widgets.revolver.size = newValue
                options: [
                    { displayName: "Small", value: 240 },
                    { displayName: "Medium", value: 300 },
                    { displayName: "Large", value: 380 }
                ]
            }
        }
    }
}
