import QtQuick
import Quickshell
import Quickshell.Io
import QtQuick.Layouts
import qs.services
import qs.modules.common
import qs.modules.common.functions
import qs.modules.common.widgets

ContentPage {
    forceWidth: true

    Process {
        id: translationProc
        property string locale: ""
        command: [Directories.aiTranslationScriptPath, translationProc.locale]
    }

    ContentSection {
        icon: "volume_up"
        title: Translation.tr("Audio")

        ConfigSwitch {
            buttonIcon: "hearing"
            text: Translation.tr("Earbang protection")
            checked: Config.options.audio.protection.enable
            onCheckedChanged: {
                Config.options.audio.protection.enable = checked;
            }
            StyledToolTip {
                text: Translation.tr("Prevents abrupt increments and restricts volume limit")
            }
        }
        ConfigRow {
            enabled: Config.options.audio.protection.enable
            ConfigSpinBox {
                icon: "arrow_warm_up"
                text: Translation.tr("Max allowed increase")
                value: Config.options.audio.protection.maxAllowedIncrease
                from: 0
                to: 100
                stepSize: 2
                onValueChanged: {
                    Config.options.audio.protection.maxAllowedIncrease = value;
                }
            }
            ConfigSpinBox {
                icon: "vertical_align_top"
                text: Translation.tr("Volume limit")
                value: Config.options.audio.protection.maxAllowed
                from: 0
                to: 154 // pavucontrol allows up to 153%
                stepSize: 2
                onValueChanged: {
                    Config.options.audio.protection.maxAllowed = value;
                }
            }
        }
    }

    ContentSection {
        icon: "battery_android_full"
        title: Translation.tr("Battery")

        ConfigRow {
            uniform: true
            ConfigSpinBox {
                icon: "warning"
                text: Translation.tr("Low warning")
                value: Config.options.battery.low
                from: 0
                to: 100
                stepSize: 5
                onValueChanged: {
                    Config.options.battery.low = value;
                }
            }
            ConfigSpinBox {
                icon: "dangerous"
                text: Translation.tr("Critical warning")
                value: Config.options.battery.critical
                from: 0
                to: 100
                stepSize: 5
                onValueChanged: {
                    Config.options.battery.critical = value;
                }
            }
        }
        ConfigRow {
            uniform: false
            Layout.fillWidth: false
            ConfigSwitch {
                buttonIcon: "pause"
                text: Translation.tr("Automatic suspend")
                checked: Config.options.battery.automaticSuspend
                onCheckedChanged: {
                    Config.options.battery.automaticSuspend = checked;
                }
                StyledToolTip {
                    text: Translation.tr("Automatically suspends the system when battery is low")
                }
            }
            ConfigSpinBox {
                enabled: Config.options.battery.automaticSuspend
                text: Translation.tr("at")
                value: Config.options.battery.suspend
                from: 0
                to: 100
                stepSize: 5
                onValueChanged: {
                    Config.options.battery.suspend = value;
                }
            }
        }
        ConfigRow {
            uniform: true
            ConfigSpinBox {
                icon: "charger"
                text: Translation.tr("Full warning")
                value: Config.options.battery.full
                from: 0
                to: 101
                stepSize: 5
                onValueChanged: {
                    Config.options.battery.full = value;
                }
            }
        }
    }

    ContentSection {
        icon: "language"
        title: Translation.tr("Language")

        ContentSubsection {
            title: Translation.tr("Interface Language")
            tooltip: Translation.tr("Select the language for the user interface.\n\"Auto\" will use your system's locale.")

            StyledComboBox {
                id: languageSelector
                buttonIcon: "language"
                textRole: "displayName"

                model: [
                    {
                        displayName: Translation.tr("Auto (System)"),
                        value: "auto"
                    },
                    ...Translation.allAvailableLanguages.map(lang => {
                        return {
                            displayName: lang,
                            value: lang
                        };
                    })]

                currentIndex: {
                    const index = model.findIndex(item => item.value === Config.options.language.ui);
                    return index !== -1 ? index : 0;
                }

                onActivated: index => {
                    Config.options.language.ui = model[index].value;
                }
            }
        }
        ContentSubsection {
            title: Translation.tr("Generate translation with Gemini")
            tooltip: Translation.tr("You'll need to enter your Gemini API key first.\nType /key on the sidebar for instructions.")

            ConfigRow {
                MaterialTextArea {
                    id: localeInput
                    Layout.fillWidth: true
                    placeholderText: Translation.tr("Locale code, e.g. fr_FR, de_DE, zh_CN...")
                    text: Config.options.language.ui === "auto" ? Qt.locale().name : Config.options.language.ui
                }
                RippleButtonWithIcon {
                    id: generateTranslationBtn
                    Layout.fillHeight: true
                    nerdIcon: ""
                    enabled: !translationProc.running || (translationProc.locale !== localeInput.text.trim())
                    mainText: enabled ? Translation.tr("Generate\nTypically takes 2 minutes") : Translation.tr("Generating...\nDon't close this window!")
                    onClicked: {
                        translationProc.locale = localeInput.text.trim();
                        translationProc.running = false;
                        translationProc.running = true;
                    }
                }
            }
        }
    }

    ContentSection {
        icon: "rule"
        title: Translation.tr("Policies")

        ConfigRow {

            // AI policy
            ColumnLayout {
                ContentSubsectionLabel {
                    text: Translation.tr("AI")
                }

                ConfigSelectionArray {
                    currentValue: Config.options.policies.ai
                    onSelected: newValue => {
                        Config.options.policies.ai = newValue;
                    }
                    options: [
                        {
                            displayName: Translation.tr("No"),
                            icon: "close",
                            value: 0
                        },
                        {
                            displayName: Translation.tr("Yes"),
                            icon: "check",
                            value: 1
                        },
                        {
                            displayName: Translation.tr("Local only"),
                            icon: "sync_saved_locally",
                            value: 2
                        }
                    ]
                }
            }

            // Weeb policy
            ColumnLayout {

                ContentSubsectionLabel {
                    text: Translation.tr("Weeb")
                }

                ConfigSelectionArray {
                    currentValue: Config.options.policies.weeb
                    onSelected: newValue => {
                        Config.options.policies.weeb = newValue;
                    }
                    options: [
                        {
                            displayName: Translation.tr("No"),
                            icon: "close",
                            value: 0
                        },
                        {
                            displayName: Translation.tr("Yes"),
                            icon: "check",
                            value: 1
                        },
                        {
                            displayName: Translation.tr("Closet"),
                            icon: "ev_shadow",
                            value: 2
                        }
                    ]
                }
            }
        }
    }

    ContentSection {
        icon: "notification_sound"
        title: Translation.tr("Sounds")
        ConfigRow {
            uniform: true
            ConfigSwitch {
                buttonIcon: "battery_android_full"
                text: Translation.tr("Battery")
                checked: Config.options.sounds.battery
                onCheckedChanged: {
                    Config.options.sounds.battery = checked;
                }
            }
            ConfigSwitch {
                buttonIcon: "av_timer"
                text: Translation.tr("Pomodoro")
                checked: Config.options.sounds.pomodoro
                onCheckedChanged: {
                    Config.options.sounds.pomodoro = checked;
                }
            }
        }
    }

    ContentSection {
        id: alarmSection
        icon: "alarm"
        title: Translation.tr("Calendar alarm")

        readonly property var builtIn: ["smoke", "tornado", "beep", "chime", "silent"]
        function choice(value) {
            return alarmSection.builtIn.includes(value) || value === "" || value === "none" ? value : "file";
        }
        readonly property var soundOptions: [
            { displayName: Translation.tr("Smoke alarm"), icon: "detector_smoke", value: "smoke" },
            { displayName: Translation.tr("Tornado siren"), icon: "tornado", value: "tornado" },
            { displayName: Translation.tr("Alarm clock"), icon: "alarm", value: "beep" },
            { displayName: Translation.tr("Chime"), icon: "notifications", value: "chime" },
            { displayName: Translation.tr("Silent"), icon: "notifications_off", value: "silent" },
            { displayName: Translation.tr("A file"), icon: "audio_file", value: "file" }
        ]

        StyledText {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            color: Appearance.colors.colSubtext
            font.pixelSize: Appearance.font.pixelSize.smallie
            text: Translation.tr("Turn an alarm on for an event in the calendar (the alarm button when you add it, or the one beside it). At its time the first sound plays at your current volume; if nobody stops it, the second takes over. Enter or Escape stops it, S snoozes it.")
        }

        ContentSubsection {
            title: Translation.tr("First sound")
            ConfigSelectionArray {
                currentValue: alarmSection.choice(Config.options.calendar.alarm.firstSound)
                onSelected: newValue => {
                    Config.options.calendar.alarm.firstSound = newValue === "file" ? "~/Music/alarm.ogg" : newValue;
                }
                options: alarmSection.soundOptions
            }
            MaterialTextArea {
                visible: alarmSection.choice(Config.options.calendar.alarm.firstSound) === "file"
                Layout.fillWidth: true
                placeholderText: Translation.tr("Sound file, e.g. ~/Music/alarm.ogg")
                text: Config.options.calendar.alarm.firstSound
                onTextChanged: {
                    if (text.trim() !== "" && text.trim() !== Config.options.calendar.alarm.firstSound)
                        Config.options.calendar.alarm.firstSound = text.trim();
                }
            }
        }

        ContentSubsection {
            title: Translation.tr("Then, if it isn't stopped")
            ConfigSelectionArray {
                currentValue: alarmSection.choice(Config.options.calendar.alarm.secondSound)
                onSelected: newValue => {
                    Config.options.calendar.alarm.secondSound = newValue === "file" ? "~/Music/alarm.ogg" : newValue;
                }
                options: alarmSection.soundOptions.concat([{ displayName: Translation.tr("Keep the first"), icon: "block", value: "none" }])
            }
            MaterialTextArea {
                visible: alarmSection.choice(Config.options.calendar.alarm.secondSound) === "file"
                Layout.fillWidth: true
                placeholderText: Translation.tr("Sound file, e.g. ~/Music/siren.ogg")
                text: Config.options.calendar.alarm.secondSound
                onTextChanged: {
                    if (text.trim() !== "" && text.trim() !== Config.options.calendar.alarm.secondSound)
                        Config.options.calendar.alarm.secondSound = text.trim();
                }
            }
        }

        ConfigSpinBox {
            icon: "timer"
            text: Translation.tr("Seconds before the second sound")
            value: Config.options.calendar.alarm.escalateAfter
            from: 5
            to: 600
            stepSize: 5
            onValueChanged: Config.options.calendar.alarm.escalateAfter = value
        }
        ConfigSpinBox {
            icon: "snooze"
            text: Translation.tr("Snooze (minutes)")
            value: Config.options.calendar.alarm.snoozeMinutes
            from: 1
            to: 60
            stepSize: 1
            onValueChanged: Config.options.calendar.alarm.snoozeMinutes = value
        }
        ConfigSpinBox {
            icon: "timer_off"
            text: Translation.tr("Stop ringing after (minutes)")
            value: Config.options.calendar.alarm.stopAfter
            from: 1
            to: 120
            stepSize: 1
            onValueChanged: Config.options.calendar.alarm.stopAfter = value
        }
        ConfigRow {
            uniform: true
            ConfigSwitch {
                buttonIcon: "alarm_add"
                text: Translation.tr("New timed events have an alarm")
                checked: Config.options.calendar.alarm.alarmByDefault
                onCheckedChanged: Config.options.calendar.alarm.alarmByDefault = checked
            }
            RippleButtonWithIcon {
                buttonRadius: Appearance.rounding.full
                materialIcon: "play_arrow"
                mainText: Translation.tr("Test the alarm")
                onClicked: Quickshell.execDetached(["qs", "-c", "ii", "ipc", "call", "alarm", "test"])
                StyledToolTip {
                    text: "qs -c ii ipc call alarm test"
                }
            }
        }
    }

    ContentSection {
        icon: "nest_clock_farsight_analog"
        title: Translation.tr("Time")

        ConfigSwitch {
            buttonIcon: "pace"
            text: Translation.tr("Second precision")
            checked: Config.options.time.secondPrecision
            onCheckedChanged: {
                Config.options.time.secondPrecision = checked;
            }
            StyledToolTip {
                text: Translation.tr("Enable if you want clocks to show seconds accurately")
            }
        }

        ContentSubsection {
            title: Translation.tr("Format")
            tooltip: ""

            ConfigSelectionArray {
                currentValue: Config.options.time.format
                onSelected: newValue => {
                    if (newValue === "hh:mm") {
                        Quickshell.execDetached(["bash", "-c", `sed -i 's/\\TIME12\\b/TIME/' '${FileUtils.trimFileProtocol(Directories.config)}/hypr/hyprlock.conf'`]);
                    } else {
                        Quickshell.execDetached(["bash", "-c", `sed -i 's/\\TIME\\b/TIME12/' '${FileUtils.trimFileProtocol(Directories.config)}/hypr/hyprlock.conf'`]);
                    }

                    Config.options.time.format = newValue;
                }
                options: [
                    {
                        displayName: Translation.tr("24h"),
                        value: "hh:mm"
                    },
                    {
                        displayName: Translation.tr("12h am/pm"),
                        value: "h:mm ap"
                    },
                    {
                        displayName: Translation.tr("12h AM/PM"),
                        value: "h:mm AP"
                    },
                ]
            }
        }
    }

    ContentSection {
        icon: "work_alert"
        title: Translation.tr("Work safety")

        ConfigSwitch {
            buttonIcon: "assignment"
            text: Translation.tr("Hide clipboard images copied from sussy sources")
            checked: Config.options.workSafety.enable.clipboard
            onCheckedChanged: {
                Config.options.workSafety.enable.clipboard = checked;
            }
        }
        ConfigSwitch {
            buttonIcon: "wallpaper"
            text: Translation.tr("Hide sussy/anime wallpapers")
            checked: Config.options.workSafety.enable.wallpaper
            onCheckedChanged: {
                Config.options.workSafety.enable.wallpaper = checked;
            }
        }
    }
}
