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
 * next. Hover (or click, with click-to-show tooltips) for sunrise, sunset, day length and the next theme change,
 * such as "Red Sun at sunset, in 2 h 10 min".
 *
 * The times come from `halcyon-theme auto day`, worked out on this computer for the location in Settings >
 * Halcyon (Auto-apply), or else the bar's weather location. Clicking opens Settings > Halcyon.
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

    function dayLength() {
        if (!root.day.sunrise || !root.day.sunset)
            return "";
        const [h1, m1] = root.day.sunrise.split(":").map(Number);
        const [h2, m2] = root.day.sunset.split(":").map(Number);
        return root.minutesText((h2 * 60 + m2) - (h1 * 60 + m1));
    }

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
        onTriggered: root.refresh()
    }
    Connections {
        target: Config.options.halcyon
        function onThemeChanged() { root.refresh(); }
        function onAutoApplyChanged() { root.refresh(); }
        function onLocationChanged() { root.refresh(); }
    }

    SunArc {
        id: dial
        anchors.centerIn: parent
        progress: root.day.progress
        ring: root.redSun
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
                    visible: !root.day.location
                    icon: "location_off"
                    label: Translation.tr("No location yet: set one in Settings > Halcyon")
                    value: ""
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
