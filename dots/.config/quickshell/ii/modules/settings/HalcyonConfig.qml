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

    Timer {
        id: cursorTimer
        interval: 700
        onTriggered: Quickshell.execDetached([page.tool, "cursor", "apply"])
    }

    function applyCursor() {
        if (page.ready)
            cursorTimer.restart();
    }

    readonly property string assistantTool: `${FileUtils.trimFileProtocol(Directories.config)}/hypr/hyprland/halcyon/assistant/halcyon-assistant`

    Timer {
        id: assistantTimer
        interval: 700
        onTriggered: Quickshell.execDetached([page.assistantTool, "reload"])
    }

    function reloadAssistant() {
        if (page.ready)
            assistantTimer.restart();
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
                },
                {
                    displayName: "Fractured Glass",
                    icon: "lens_blur",
                    value: "fractured-glass"
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
        icon: "mic"
        title: Translation.tr("Assistant")

        ConfigSwitch {
            buttonIcon: "power_settings_new"
            text: Translation.tr("Voice assistant (Super+Shift+Space)")
            checked: Config.options.halcyon.assistant.enable
            onCheckedChanged: {
                Config.options.halcyon.assistant.enable = checked;
                if (!page.ready)
                    return;
                if (checked)
                    Quickshell.execDetached(["bash", "-c", `'${page.assistantTool}' autostart >/dev/null 2>&1 &`]);
                else
                    Quickshell.execDetached([page.assistantTool, "stop"]);
            }
        }

        ContentSubsection {
            title: Translation.tr("AI")
            tooltip: Translation.tr("Auto uses an Anthropic API key if set, then your Claude plan, then Gemini, then a local Ollama model. Keys are shared with the AI sidebar.")
            ConfigSelectionArray {
                currentValue: Config.options.halcyon.assistant.provider
                onSelected: newValue => {
                    Config.options.halcyon.assistant.provider = newValue;
                    page.reloadAssistant();
                }
                options: [
                    { displayName: Translation.tr("Auto"), icon: "auto_mode", value: "auto" },
                    { displayName: Translation.tr("Claude plan"), icon: "workspace_premium", value: "claude-code" },
                    { displayName: Translation.tr("Claude API"), icon: "neurology", value: "claude" },
                    { displayName: "Gemini", icon: "star", value: "gemini" },
                    { displayName: Translation.tr("Ollama (local)"), icon: "computer", value: "ollama" },
                    { displayName: Translation.tr("OpenAI-compatible"), icon: "api", value: "openai" }
                ]
            }
        }

        RowLayout {
            StyledText {
                Layout.leftMargin: 10
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: Appearance.colors.colSubtext
                font.pixelSize: Appearance.font.pixelSize.smallie
                text: Translation.tr("No API key? Use your Claude Pro or Max plan: sign in to Claude Code, Anthropic's own app, and the assistant uses it. Counts against your plan's usage.")
            }
            RippleButtonWithIcon {
                buttonRadius: Appearance.rounding.full
                materialIcon: "login"
                mainText: Translation.tr("Sign in with Claude")
                onClicked: {
                    // A terminal, since signing in may ask to install Claude Code
                    // and to paste a code back from the browser.
                    Quickshell.execDetached(["bash", "-c", `${Config.options.apps.terminal} bash -c "'${page.assistantTool}' login; read -rp 'Press Enter to close. '"`]);
                }
                StyledToolTip {
                    text: "halcyon assistant login"
                }
            }
        }

        ConfigRow {
            uniform: true
            ConfigSwitch {
                buttonIcon: "record_voice_over"
                text: Translation.tr("\"Hey Halcyon\"")
                checked: Config.options.halcyon.assistant.wakeWord
                onCheckedChanged: {
                    Config.options.halcyon.assistant.wakeWord = checked;
                    page.reloadAssistant();
                }
                StyledToolTip {
                    text: Translation.tr("Listens for the wake phrase all the time, entirely on this computer. Needs: halcyon assistant setup --wake")
                }
            }
            ConfigSwitch {
                buttonIcon: "volume_up"
                text: Translation.tr("Speak replies")
                checked: Config.options.halcyon.assistant.speak
                onCheckedChanged: {
                    Config.options.halcyon.assistant.speak = checked;
                    page.reloadAssistant();
                }
            }
        }

        ConfigSwitch {
            buttonIcon: "touch_app"
            text: Translation.tr("Let it control the desktop")
            checked: Config.options.halcyon.assistant.allowActions
            onCheckedChanged: {
                Config.options.halcyon.assistant.allowActions = checked;
                page.reloadAssistant();
            }
            StyledToolTip {
                text: Translation.tr("Apps, volume, brightness, media, workspaces, themes, screenshots, lock, web search. Nothing else: it can't run commands.")
            }
        }

        ContentSubsection {
            title: Translation.tr("Speech recognition")
            tooltip: Translation.tr("Whisper, running on this computer. Bigger is more accurate but slower. Set up with: halcyon assistant setup")
            ConfigSelectionArray {
                currentValue: Config.options.halcyon.assistant.speechModel
                onSelected: newValue => {
                    Config.options.halcyon.assistant.speechModel = newValue;
                    page.reloadAssistant();
                }
                options: [
                    { displayName: Translation.tr("Fast"), value: "tiny" },
                    { displayName: Translation.tr("Balanced"), value: "base" },
                    { displayName: Translation.tr("Accurate"), value: "small" }
                ]
            }
        }
    }

    ContentSection {
        icon: "arrow_selector_tool"
        title: Translation.tr("Cursor")

        ConfigSwitch {
            buttonIcon: "arrow_selector_tool"
            text: Translation.tr("Halcyon Glass cursor")
            checked: Config.options.halcyon.cursor.enable
            onCheckedChanged: {
                Config.options.halcyon.cursor.enable = checked;
                page.applyCursor();
            }
            StyledToolTip {
                text: Translation.tr("Off uses illogical-impulse's Bibata cursor")
            }
        }

        ContentSubsection {
            title: Translation.tr("Size")
            ConfigSelectionArray {
                currentValue: Config.options.halcyon.cursor.size
                onSelected: newValue => {
                    Config.options.halcyon.cursor.size = newValue;
                    page.applyCursor();
                }
                options: [24, 32, 48, 64].map(size => ({
                    displayName: `${size}px`,
                    value: size
                }))
            }
        }
    }

    ContentSection {
        icon: "water_drop"
        title: Translation.tr("Glass")

        ContentSubsection {
            title: Translation.tr("Screen effects")
            tooltip: Translation.tr("Only at the Full effects level, with a glass theme. Fractured Glass has the lens only: no ripples or edge fringe")

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

            ConfigSlider {
                buttonIcon: "animation"
                text: Translation.tr("Lens bounce")
                value: Config.options.halcyon.glass.lensBounce
                from: 0
                to: 1
                stopIndicatorValues: [0.8]
                onValueChanged: {
                    Config.options.halcyon.glass.lensBounce = value;
                    page.refresh();
                }
            }
        }

        ContentSubsection {
            title: Translation.tr("Glass windows")
            tooltip: Translation.tr("For themes with translucent windows (Shattered Glass, Fractured Glass), at Light or Full")

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
