import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Wayland
import qs.Config
import qs.Components
import qs.Services

/**
 * Desktop widgets.
 *
 * A clock, system load, battery and now-playing, drawn on the wallpaper
 * layer rather than over the windows — so they are part of the desktop
 * you see when everything is minimised, not a panel you dismiss.
 *
 * The load figures are read once every few seconds, and only while the
 * dashboard is actually visible.
 */
Scope {
    id: root

    readonly property bool shown: Overlays.isOpen("dashboard")

    SystemClock {
        id: clock
        enabled: root.shown
        precision: SystemClock.Minutes
    }

    property real cpuPercent: 0
    property real memoryPercent: 0
    property real memoryUsedGb: 0
    property real memoryTotalGb: 0

    /** Previous /proc/stat sample, for the delta CPU load is computed from. */
    property var lastCpu: null

    Timer {
        running: root.shown
        interval: Power.onBattery ? 6000 : 3000
        repeat: true
        triggeredOnStart: true
        onTriggered: {
            statReader.reload();
            memReader.reload();
        }
    }

    FileView {
        id: statReader
        path: "/proc/stat"
        printErrors: false
        blockLoading: false
        onLoaded: {
            const line = this.text().split("\n")[0] ?? "";
            const fields = line.trim().split(/\s+/).slice(1).map(Number);
            if (fields.length < 4)
                return;
            const idle = fields[3] + (fields[4] ?? 0);
            const total = fields.reduce((sum, value) => sum + value, 0);
            if (root.lastCpu) {
                const idleDelta = idle - root.lastCpu.idle;
                const totalDelta = total - root.lastCpu.total;
                if (totalDelta > 0)
                    root.cpuPercent = Math.max(0, Math.min(100,
                        (1 - idleDelta / totalDelta) * 100));
            }
            root.lastCpu = { idle: idle, total: total };
        }
    }

    FileView {
        id: memReader
        path: "/proc/meminfo"
        printErrors: false
        blockLoading: false
        onLoaded: {
            let total = 0;
            let available = 0;
            for (const line of this.text().split("\n")) {
                if (line.indexOf("MemTotal:") === 0)
                    total = parseInt(line.replace(/\D+/g, ""), 10);
                else if (line.indexOf("MemAvailable:") === 0)
                    available = parseInt(line.replace(/\D+/g, ""), 10);
            }
            if (total > 0) {
                root.memoryTotalGb = total / 1048576;
                root.memoryUsedGb = (total - available) / 1048576;
                root.memoryPercent = (1 - available / total) * 100;
            }
        }
    }

    Variants {
        model: Quickshell.screens

        LazyLoader {
            required property var modelData
            active: root.shown

            PanelWindow {
                screen: modelData

                anchors { top: true; right: true }
                margins {
                    top: Config.get("bar.height", 34) + Theme.spacingLg
                    right: Theme.spacingLg
                }
                exclusionMode: ExclusionMode.Ignore
                color: "transparent"
                focusable: false

                // The background layer, so widgets sit on the wallpaper
                // and never over a window.
                WlrLayershell.namespace: "halcyon-dashboard"
                WlrLayershell.layer: WlrLayer.Bottom
                WlrLayershell.keyboardFocus: WlrKeyboardFocus.None

                implicitWidth: 300
                implicitHeight: widgets.implicitHeight

                ColumnLayout {
                    id: widgets
                    anchors.fill: parent
                    spacing: Theme.spacingMd

                    opacity: root.shown ? 1 : 0
                    Behavior on opacity {
                        enabled: Theme.animationsEnabled
                        NumberAnimation { duration: Theme.durOverlay }
                    }

                    // ── Clock ────────────────────────────────────────

                    GlassSurface {
                        Layout.fillWidth: true
                        level: 2
                        radius: Theme.radiusXl
                        padding: Theme.panelPadding
                        implicitHeight: clockColumn.implicitHeight + padding * 2

                        ColumnLayout {
                            id: clockColumn
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            spacing: 0

                            Label {
                                Layout.fillWidth: true
                                text: Qt.formatDateTime(clock.date ?? new Date(), "HH:mm")
                                variant: "hero"
                            }

                            Label {
                                Layout.fillWidth: true
                                text: Qt.formatDateTime(clock.date ?? new Date(), "dddd, d MMMM")
                                variant: "footnote"
                                tone: "secondary"
                            }
                        }
                    }

                    // ── System ───────────────────────────────────────

                    GlassSurface {
                        Layout.fillWidth: true
                        level: 2
                        radius: Theme.radiusXl
                        padding: Theme.panelPadding
                        implicitHeight: statsColumn.implicitHeight + padding * 2

                        ColumnLayout {
                            id: statsColumn
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            spacing: Theme.spacingSm

                            MeterRow {
                                Layout.fillWidth: true
                                glyph: "󰻠"
                                label: "CPU"
                                value: root.cpuPercent
                                detail: Math.round(root.cpuPercent) + "%"
                            }

                            MeterRow {
                                Layout.fillWidth: true
                                glyph: "󰍛"
                                label: "Memory"
                                value: root.memoryPercent
                                detail: root.memoryUsedGb.toFixed(1) + " / "
                                    + root.memoryTotalGb.toFixed(1) + " GiB"
                            }

                            MeterRow {
                                Layout.fillWidth: true
                                visible: Power.hasBattery
                                glyph: Power.glyph
                                label: "Battery"
                                value: Power.percentage
                                detail: Power.remaining.length > 0
                                    ? Power.remaining
                                    : Power.percent + "%"
                                fill: Power.critical ? Theme.danger
                                    : (Power.low ? Theme.warning : Theme.accent)
                            }
                        }
                    }

                    // ── Now playing ──────────────────────────────────

                    GlassSurface {
                        Layout.fillWidth: true
                        visible: Media.hasPlayer
                        level: 2
                        radius: Theme.radiusXl
                        padding: Theme.panelPadding
                        implicitHeight: mediaColumn.implicitHeight + padding * 2

                        ColumnLayout {
                            id: mediaColumn
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            spacing: 1

                            Label {
                                Layout.fillWidth: true
                                text: "Now Playing"
                                variant: "caption"
                                tone: "tertiary"
                            }

                            Label {
                                Layout.fillWidth: true
                                text: Media.title
                                variant: "body"
                                font.weight: Theme.weightMedium
                            }

                            Label {
                                Layout.fillWidth: true
                                visible: Media.artist.length > 0
                                text: Media.artist
                                variant: "footnote"
                                tone: "secondary"
                            }
                        }
                    }

                    // ── HyperNix ─────────────────────────────────────

                    GlassSurface {
                        Layout.fillWidth: true
                        visible: HyperNix.available && Config.get("hypernix.showWidget", true)
                        level: 2
                        radius: Theme.radiusXl
                        padding: Theme.panelPadding
                        implicitHeight: hypernixColumn.implicitHeight + padding * 2

                        ColumnLayout {
                            id: hypernixColumn
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            spacing: 1

                            Label {
                                Layout.fillWidth: true
                                text: "HyperNix " + HyperNix.version
                                variant: "caption"
                                tone: "tertiary"
                            }

                            Label {
                                Layout.fillWidth: true
                                text: HyperNix.summary
                                variant: "footnote"
                                tone: "secondary"
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                }
            }
        }
    }

    onShownChanged: {
        HyperNix.watchers += root.shown ? 1 : -1;
        if (HyperNix.watchers < 0)
            HyperNix.watchers = 0;
    }
}
