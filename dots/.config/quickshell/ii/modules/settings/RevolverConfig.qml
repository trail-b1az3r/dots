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

        ConfigSwitch {
            buttonIcon: "rocket_launch"
            text: Translation.tr("Launch animation when it starts a game")
            checked: Config.options.background.widgets.revolver.launchAnimation
            onCheckedChanged: Config.options.background.widgets.revolver.launchAnimation = checked
            StyledToolTip {
                text: Translation.tr("A shot from the drum, and the game's own art flying in while it starts")
            }
        }

        RippleButtonWithIcon {
            Layout.leftMargin: 10
            buttonRadius: Appearance.rounding.full
            materialIcon: "play_arrow"
            mainText: Translation.tr("Preview the launch animation")
            enabled: Config.options.background.widgets.revolver.launchAnimation && Config.options.background.widgets.revolver.enable
            onClicked: Quickshell.execDetached(["qs", "-c", "ii", "ipc", "call", "revolver", "preview"])
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

    ContentSection {
        icon: "visibility"
        title: Translation.tr("Red Sun sequence")

        StyledText {
            Layout.fillWidth: true
            Layout.leftMargin: 10
            wrapMode: Text.Wrap
            color: Appearance.colors.colSubtext
            font.pixelSize: Appearance.font.pixelSize.smallie
            text: Translation.tr("In Red Sun, at the Full effects level, a real spin of the ring breaks the screen: an eye opens in the sun, finds the car, and the tape rewinds. It is drawn over the whole screen while it runs (about 10 seconds), so Light is easier on a slower GPU or a 4K screen.")
        }
        ConfigSwitch {
            buttonIcon: "broken_image"
            text: Translation.tr("A spin breaks the screen")
            checked: Config.options.background.widgets.revolver.sequence
            onCheckedChanged: Config.options.background.widgets.revolver.sequence = checked
        }
        ConfigSwitch {
            buttonIcon: "visibility"
            enabled: Config.options.background.widgets.revolver.sequence
            text: Translation.tr("The eye")
            checked: Config.options.background.widgets.revolver.eye
            onCheckedChanged: Config.options.background.widgets.revolver.eye = checked
            StyledToolTip {
                text: Translation.tr("Off: the sun's hole stays an empty glowing void")
            }
        }
        ConfigSwitch {
            buttonIcon: "videocam"
            enabled: Config.options.background.widgets.revolver.sequence
            text: Translation.tr("The tape and rewind")
            checked: Config.options.background.widgets.revolver.tape
            onCheckedChanged: Config.options.background.widgets.revolver.tape = checked
            StyledToolTip {
                text: Translation.tr("Off: after the eye, the broken screen fades back (about 7 seconds in all)")
            }
        }
        ContentSubsection {
            title: Translation.tr("Quality")
            ConfigSelectionArray {
                currentValue: Config.options.background.widgets.revolver.quality
                onSelected: newValue => Config.options.background.widgets.revolver.quality = newValue
                options: [
                    { displayName: Translation.tr("Full"), value: "full" },
                    { displayName: Translation.tr("Light"), value: "light" }
                ]
            }
        }
    }
}
