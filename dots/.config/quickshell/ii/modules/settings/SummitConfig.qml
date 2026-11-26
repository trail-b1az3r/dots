import QtQuick
import Quickshell
import Quickshell.Io
import QtQuick.Layouts
import qs.services
import qs.modules.common
import qs.modules.common.functions
import qs.modules.common.widgets

// Settings > Summit, while Summit is the shell: its notifications (and the importance model), the side menu, the bar,
// hypr mode and its fonts. Stored in ~/.config/halcyon/summit.json, which Summit reads again as soon as it changes
// (its services/Prefs.qml has the defaults and what each one does).
ContentPage {
    id: page
    forceWidth: true

    readonly property string path: `${FileUtils.trimFileProtocol(Directories.config)}/halcyon/summit.json`
    property var data: ({})
    // Controls report their first values while the page is built: only changes after that are saved.
    property bool ready: false
    Timer { interval: 300; running: true; onTriggered: page.ready = true }

    function get(key, fallback) {
        let node = page.data;
        for (const part of key.split(".")) {
            if (node === null || typeof node !== "object" || !(part in node))
                return fallback;
            node = node[part];
        }
        return node;
    }
    function set(key, value) {
        if (!page.ready || page.get(key, undefined) === value)
            return;
        const next = JSON.parse(JSON.stringify(page.data ?? {}));
        const parts = key.split(".");
        let node = next;
        for (const part of parts.slice(0, -1)) {
            if (typeof node[part] !== "object" || node[part] === null)
                node[part] = {};
            node = node[part];
        }
        node[parts[parts.length - 1]] = value;
        page.data = next;
        file.setText(JSON.stringify(next, null, 2) + "\n");
    }

    FileView {
        id: file
        path: page.path
        blockLoading: true
        printErrors: false
        onLoaded: {
            try {
                const parsed = JSON.parse(text());
                page.data = parsed && typeof parsed === "object" ? parsed : {};
            } catch (e) {
                page.data = {};
            }
        }
        onLoadFailed: page.data = {}
    }

    ContentSection {
        icon: "notifications"
        title: Translation.tr("Notifications")

        ConfigSwitch {
            buttonIcon: "notifications_active"
            text: Translation.tr("Popups in the corner")
            checked: page.get("notifications.popups", true)
            onCheckedChanged: page.set("notifications.popups", checked)
            StyledToolTip {
                text: Translation.tr("New notifications show in the top right corner for a few seconds. They all stay in the side menu until you dismiss them.")
            }
        }
        ConfigSwitch {
            buttonIcon: "do_not_disturb_on"
            text: Translation.tr("Do not disturb")
            checked: page.get("notifications.do_not_disturb", false)
            onCheckedChanged: page.set("notifications.do_not_disturb", checked)
            StyledToolTip {
                text: Translation.tr("Nothing pops up; notifications still wait in the side menu. Also \"Silent\" in the side menu.")
            }
        }

        ContentSubsection {
            title: Translation.tr("Important notifications")
            tooltip: Translation.tr("A tiny model on this computer reads each notification (its app, title and text: nothing is sent anywhere) and decides whether it matters now: a code, a call, someone who needs you, a meeting about to start, something that failed. Those open under the clock, wider and with a one-line summary, then fade after three seconds. Never over a fullscreen app.")

            ConfigSwitch {
                buttonIcon: "neurology"
                text: Translation.tr("Show important ones under the clock")
                checked: page.get("notifications.important_banner", true)
                onCheckedChanged: page.set("notifications.important_banner", checked)
            }
            ConfigSpinBox {
                icon: "tune"
                text: Translation.tr("How sure the model must be (%)")
                from: 50
                to: 95
                stepSize: 5
                value: Math.round(page.get("notifications.threshold", 0.6) * 100)
                onValueChanged: page.set("notifications.threshold", value / 100)
                StyledToolTip {
                    text: Translation.tr("Higher lets fewer through: only what it is very sure about. The rest show as ordinary popups.")
                }
            }
        }
    }

    ContentSection {
        icon: "right_panel_open"
        title: Translation.tr("Side menu")

        ConfigSwitch {
            buttonIcon: "border_right"
            text: Translation.tr("Open it at the right edge of the screen")
            checked: page.get("side_menu.edge", true)
            onCheckedChanged: page.set("side_menu.edge", checked)
            StyledToolTip {
                text: Translation.tr("Push the pointer against the right edge of the rightmost screen to open the side menu (not over a fullscreen app). A click on the bar's right group always opens it.")
            }
        }
        ConfigSpinBox {
            icon: "timer"
            text: Translation.tr("Wait at the edge first (ms)")
            from: 0
            to: 1000
            stepSize: 50
            value: page.get("side_menu.edge_delay", 150)
            onValueChanged: page.set("side_menu.edge_delay", value)
        }
    }

    ContentSection {
        icon: "toast"
        title: Translation.tr("Bar")

        ConfigSwitch {
            buttonIcon: "light_mode"
            text: Translation.tr("Brightness on the left")
            checked: page.get("bar.brightness", true)
            onCheckedChanged: page.set("bar.brightness", checked)
            StyledToolTip {
                text: Translation.tr("A sun beside the launcher: scroll it (or the launcher) to change the brightness, click it for the slider. Below the sun on the slider the screen is dimmed further than its backlight goes.")
            }
        }
        ConfigSwitch {
            buttonIcon: "keyboard"
            text: Translation.tr("Hypr mode's glow round the screens")
            checked: page.get("hypr_mode.glow", true)
            onCheckedChanged: page.set("hypr_mode.glow", checked)
            StyledToolTip {
                text: Translation.tr("While hypr mode is on (Super+Ctrl+H) a glow traces round every screen. Its keys always show above the dock, and HYPR on the bar.")
            }
        }
    }

    ContentSection {
        icon: "match_case"
        title: Translation.tr("Fonts")

        ContentSubsection {
            title: Translation.tr("Text")
            ConfigSelectionArray {
                currentValue: page.get("fonts.text", "")
                onSelected: newValue => page.set("fonts.text", newValue)
                options: [
                    { displayName: "Summit Sans", icon: "brand_family", value: "" },
                    { displayName: "Inter", icon: "text_fields", value: "Inter" },
                    { displayName: Translation.tr("The system's"), icon: "computer", value: "sans-serif" }
                ]
            }
        }
        ContentSubsection {
            title: Translation.tr("Code")
            tooltip: Translation.tr("Keys, codes, the timer and the clipboard. Iosevka Nerd Font comes with Summit's package (ttf-iosevka-nerd).")
            ConfigSelectionArray {
                currentValue: page.get("fonts.code", "")
                onSelected: newValue => page.set("fonts.code", newValue)
                options: [
                    { displayName: "Iosevka Nerd Font", icon: "code", value: "" },
                    { displayName: "JetBrains Mono", icon: "terminal", value: "JetBrainsMono Nerd Font" },
                    { displayName: Translation.tr("The system's"), icon: "computer", value: "monospace" }
                ]
            }
        }
        RippleButtonWithIcon {
            materialIcon: "sentiment_very_dissatisfied"
            mainText: Translation.tr("Everything in RightFont, until I restart")
            onClicked: Quickshell.execDetached([`${FileUtils.trimFileProtocol(Directories.config)}/hypr/hyprland/halcyon/halcyon-theme`, "fonts", "right-font", "on"])
            StyledToolTip {
                text: Translation.tr("\"The most confusing font possible\" (Right of the Bell). It is hard to read, so it ends with the session: restart, or run halcyon fonts right-font off.")
            }
        }
    }
}
