import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.modules.common
import qs.modules.common.widgets
import qs.modules.common.functions
import qs.services

/**
 * The sun dial: where the sun is in today's sky, between sunrise and sunset, and what the theme schedule does
 * next. At night it turns upside down and shows the moon, in tonight's phase. Hover (or click, with click-to-show tooltips) for sunrise, sunset, day length and the next theme change,
 * such as "Red Sun at sunset, in 2 h 10 min".
 *
 * The times come from `halcyon-theme auto day`, worked out on this computer for the location in Settings >
 * Halcyon (Auto-apply), else the device's location (HalcyonLocation), else the weather's place. Clicking opens Settings > Halcyon.
 */
Item {
    id: root

    readonly property string tool: `${FileUtils.trimFileProtocol(Directories.config)}/hypr/hyprland/halcyon/halcyon-theme`
    property var day: ({})
    readonly property bool redSun: Config.options.halcyon.theme === "red-sun"

    implicitWidth: dial.implicitWidth + 6
    implicitHeight: Appearance.sizes.barHeight

    function refresh() {
        dayProc.running = true;
    }

    function minutesText(total) {
        if (total === undefined || total === null)
            return "";
        const h = Math.floor(total / 60), m = total % 60;
        return h > 0 ? Translation.tr("%1 h %2 min").arg(h).arg(m) : Translation.tr("%1 min").arg(m);
    }

    function dayMinutes() {
        if (!root.day.sunrise || !root.day.sunset)
            return 0;
        const [h1, m1] = root.day.sunrise.split(":").map(Number);
        const [h2, m2] = root.day.sunset.split(":").map(Number);
        return (h2 * 60 + m2) - (h1 * 60 + m1);
    }

    function dayLength() {
        return root.dayMinutes() > 0 ? root.minutesText(root.dayMinutes()) : "";
    }

    // The moon's phase, worked out again with the sun each minute.
    property real moonPhase: dial.moonPhaseAt(new Date())
    readonly property string moonText: ({
        "new": Translation.tr("New moon"), "waxing-crescent": Translation.tr("Waxing crescent"),
        "first-quarter": Translation.tr("First quarter"), "waxing-gibbous": Translation.tr("Waxing gibbous"),
        "full": Translation.tr("Full moon"), "waning-gibbous": Translation.tr("Waning gibbous"),
        "last-quarter": Translation.tr("Last quarter"), "waning-crescent": Translation.tr("Waning crescent")
    })[dial.moonName(root.moonPhase)] ?? ""

    Process {
        id: dayProc
        command: [root.tool, "auto", "day", "--json"]
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    root.day = JSON.parse(this.text) ?? {};
                } catch (error) {
                    root.day = {};
                }
            }
        }
    }

    // The sun moves slowly: once a minute is plenty, and cheap (no network).
    Timer {
        interval: 60 * 1000
        running: true
        repeat: true
        triggeredOnStart: true
        onTriggered: {
            root.refresh();
            root.moonPhase = dial.moonPhaseAt(new Date());
        }
    }
    Connections {
        target: Config.options.halcyon
        function onThemeChanged() { root.refresh(); }
        function onAutoApplyChanged() { root.refresh(); }
        function onLocationChanged() { root.refresh(); }
    }
    Connections {
        target: HalcyonLocation
        function onUpdated() { root.refresh(); }
    }

    SunArc {
        id: dial
        anchors.centerIn: parent
        progress: root.day.progress
        dayHours: root.dayMinutes() > 0 ? root.dayMinutes() / 60 : 12
        moonPhase: root.moonPhase
        southern: !!root.day.location && root.day.location[0] < 0
        ring: root.redSun
        colMoon: root.redSun ? "#ffe2d6" : Appearance.colors.colOnLayer1
        colLine: ColorUtils.applyAlpha(Appearance.colors.colOnLayer1, 0.45)
        colSun: root.redSun ? "#ffe2d6" : Appearance.colors.colPrimary
        colGlow: root.redSun ? "#ff4940" : Appearance.colors.colPrimary
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: !Config.options.bar.tooltips.clickToShow
        acceptedButtons: Qt.LeftButton
        onClicked: Quickshell.execDetached([root.tool, "settings"])

        StyledPopup {
            hoverTarget: mouseArea

            ColumnLayout {
                anchors.centerIn: parent
                spacing: 4

                StyledPopupHeaderRow {
                    icon: root.day.progress !== undefined && root.day.progress !== null && (root.day.progress < 0 || root.day.progress > 1) ? "dark_mode" : "wb_sunny"
                    label: Translation.tr("The sun today")
                }
                StyledPopupValueRow {
                    visible: !!root.day.sunrise
                    icon: "wb_twilight"
                    label: Translation.tr("Sunrise:")
                    value: root.day.sunrise ?? ""
                }
                StyledPopupValueRow {
                    visible: !!root.day.sunset
                    icon: "routine"
                    label: Translation.tr("Sunset:")
                    value: root.day.sunset ?? ""
                }
                StyledPopupValueRow {
                    visible: root.dayLength() !== ""
                    icon: "hourglass_top"
                    label: Translation.tr("Daylight:")
                    value: root.dayLength()
                }
                StyledPopupValueRow {
                    icon: "dark_mode"
                    label: Translation.tr("Moon:")
                    value: Translation.tr("%1, %2% lit").arg(root.moonText).arg(Math.round(dial.moonLit(root.moonPhase) * 100))
                }
                StyledPopupValueRow {
                    visible: !root.day.location
                    icon: "location_off"
                    label: Translation.tr("No location yet: turn location on, or set a place in Settings > Halcyon")
                    value: ""
                }
                StyledPopupValueRow {
                    visible: !!root.day.location
                    icon: "location_on"
                    label: Translation.tr("Place:")
                    value: ({ "settings": Translation.tr("set in Settings"), "device": Translation.tr("this device's location"),
                              "weather": Translation.tr("the weather's place") })[root.day.source] ?? ""
                }
                StyledPopupValueRow {
                    visible: !!root.day.next
                    icon: "palette"
                    label: Translation.tr("Next:")
                    value: root.day.next ? Translation.tr("%1, %2 at %3 (%4), in %5")
                        .arg(root.day.next.name).arg(root.day.next.day).arg(root.day.next.at)
                        .arg(root.day.next.when).arg(root.minutesText(root.day.next.minutes))
                        + (root.day.next.weather ? " " + Translation.tr("if %1").arg(root.day.next.weather) : "") : ""
                }
            }
        }
    }
}
