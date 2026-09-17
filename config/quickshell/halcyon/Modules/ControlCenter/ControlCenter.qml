import QtQuick
import QtQuick.Layouts
import Quickshell
import qs.Config
import qs.Components
import qs.Services

/**
 * Control Center.
 *
 * Everything you reach for without opening Settings: the radios, the
 * sliders, the modes, and what is playing. One tile can be expanded at a
 * time, in place, so the panel never becomes a stack of half-open
 * accordions.
 */
OverlayWindow {
    id: root

    name: "control"
    namespaceName: "halcyon-control"
    origin: "top"
    scrim: false
    grabKeyboard: false

    /** "" | wifi | bluetooth | audio | display */
    property string expanded: ""

    onOpened: {
        root.expanded = Overlays.payload.section ?? "";
        HyperNix.watchers += 1;
        root.syncScanners();
    }
    onClosed: {
        HyperNix.watchers = Math.max(0, HyperNix.watchers - 1);
        root.expanded = "";
        root.syncScanners();
    }
    onExpandedChanged: root.syncScanners()

    /**
     * Scanning only while it is being looked at.
     *
     * A Wi-Fi scan wakes the radio; Bluetooth discovery broadcasts. Both
     * belong to the moment the list is on screen and to no other moment.
     */
    function syncScanners(): void {
        Net.scanning = root.shown && root.expanded === "wifi";
        Bt.scanning = root.shown && root.expanded === "bluetooth";
    }

    GlassSurface {
        id: panel

        anchors.right: parent.right
        anchors.top: parent.top
        anchors.topMargin: Config.get("bar.height", 34) + Theme.spacingSm
        anchors.rightMargin: Theme.spacingMd

        width: 380
        height: Math.min(
            root.height - anchors.topMargin - Theme.spacingLg,
            content.implicitHeight + padding * 2
        )
        level: 4
        radius: Theme.radiusXl
        padding: Theme.panelPadding
        tintStrength: 1.1

        Behavior on height {
            enabled: Theme.animationsEnabled && !Theme.reducedMotion
            NumberAnimation {
                duration: Theme.durQuick
                easing.type: Easing.BezierSpline
                easing.bezierCurve: Theme.easeStandard
            }
        }

        Flickable {
            anchors.fill: parent
            contentHeight: content.implicitHeight
            clip: true
            interactive: contentHeight > height
            boundsBehavior: Flickable.StopAtBounds

            ColumnLayout {
                id: content
                width: parent.width
                spacing: Theme.spacingSm

                // ── Connectivity ─────────────────────────────────────

                GridLayout {
                    Layout.fillWidth: true
                    columns: 2
                    columnSpacing: Theme.spacingSm
                    rowSpacing: Theme.spacingSm

                    ControlTile {
                        Layout.fillWidth: true
                        title: "Wi-Fi"
                        subtitle: Net.summary
                        glyph: Net.glyph
                        active: Net.wifiEnabled
                        expandable: true
                        expanded: root.expanded === "wifi"
                        enabled: Net.wifiHardwareEnabled
                        onToggled: Net.toggleWifi()
                        onExpandRequested: root.expanded = root.expanded === "wifi" ? "" : "wifi"
                    }

                    ControlTile {
                        Layout.fillWidth: true
                        title: "Bluetooth"
                        subtitle: Bt.summary
                        glyph: Bt.glyph
                        active: Bt.enabled
                        expandable: Bt.available
                        expanded: root.expanded === "bluetooth"
                        enabled: Bt.available
                        onToggled: Bt.toggle()
                        onExpandRequested: root.expanded = root.expanded === "bluetooth" ? "" : "bluetooth"
                    }
                }

                WifiPanel {
                    Layout.fillWidth: true
                    visible: root.expanded === "wifi"
                }

                BluetoothPanel {
                    Layout.fillWidth: true
                    visible: root.expanded === "bluetooth"
                }

                // ── Modes ────────────────────────────────────────────

                GridLayout {
                    Layout.fillWidth: true
                    columns: 2
                    columnSpacing: Theme.spacingSm
                    rowSpacing: Theme.spacingSm

                    ControlTile {
                        Layout.fillWidth: true
                        title: Theme.isDark ? "Dark Mode" : "Light Mode"
                        subtitle: Config.get("appearance.mode", "dark") === "auto"
                            ? "Following the wallpaper" : "Appearance"
                        glyph: Theme.isDark ? "󰽥" : "󰖨"
                        active: Theme.isDark
                        onToggled: Actions.toggleMode()
                    }

                    ControlTile {
                        Layout.fillWidth: true
                        title: "Do Not Disturb"
                        subtitle: Notifications.doNotDisturb ? "On" : "Off"
                        glyph: Notifications.doNotDisturb ? "󰂛" : "󰂚"
                        active: Notifications.doNotDisturb
                        onToggled: Notifications.setDoNotDisturb(!Notifications.doNotDisturb)
                    }

                    ControlTile {
                        Layout.fillWidth: true
                        title: "Microphone"
                        subtitle: Audio.inputMuted ? "Muted" : Audio.sourceName
                        glyph: Audio.inputGlyph
                        active: !Audio.inputMuted
                        onToggled: Audio.toggleInputMute()
                    }

                    ControlTile {
                        Layout.fillWidth: true
                        title: "Airplane Mode"
                        subtitle: (!Net.wifiEnabled && !Bt.enabled) ? "On" : "Off"
                        glyph: "󰀝"
                        active: !Net.wifiEnabled && !Bt.enabled
                        onToggled: Actions.invoke("airplane.set", { state: "toggle" })
                    }
                }

                // ── Sliders ──────────────────────────────────────────

                GlassSurface {
                    Layout.fillWidth: true
                    level: 1
                    radius: Theme.radiusLg
                    padding: Theme.panelPaddingTight
                    implicitHeight: sliders.implicitHeight + padding * 2

                    ColumnLayout {
                        id: sliders
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        spacing: Theme.spacingSm

                        GlassSlider {
                            Layout.fillWidth: true
                            glyph: Audio.glyph
                            value: Audio.volume
                            showValue: true
                            fillColor: Audio.muted ? Theme.textTertiary : Theme.accent
                            onMoved: value => Audio.setVolume(value)
                        }

                        GlassSlider {
                            Layout.fillWidth: true
                            visible: Brightness.available
                            glyph: Brightness.glyph
                            value: Brightness.percent / 100
                            showValue: true
                            onMoved: value => Brightness.set(Math.round(value * 100))
                        }

                        GlassSlider {
                            Layout.fillWidth: true
                            visible: Brightness.keyboardAvailable
                            glyph: "󰌌"
                            value: Brightness.keyboardPercent / 100
                            onMoved: value => Brightness.setKeyboard(Math.round(value * 100))
                        }
                    }
                }

                // ── Power ────────────────────────────────────────────

                GlassSurface {
                    Layout.fillWidth: true
                    level: 1
                    radius: Theme.radiusLg
                    padding: Theme.panelPaddingTight
                    implicitHeight: powerRow.implicitHeight + padding * 2

                    ColumnLayout {
                        id: powerRow
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        spacing: Theme.spacingSm

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spacingSm

                            Icon {
                                glyph: Power.glyph
                                size: 18
                                color: Power.critical ? Theme.danger : Theme.text
                            }

                            Label {
                                Layout.fillWidth: true
                                text: Power.hasBattery
                                    ? Power.percent + "%  ·  " + Power.remaining
                                    : "On AC power"
                                variant: "footnote"
                                tone: "secondary"
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spacingXs

                            Repeater {
                                model: Power.profiles

                                GlassButton {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    text: Power.profileTitle(modelData)
                                    glyph: Power.profileGlyph(modelData)
                                    variant: Power.profile === modelData ? "filled" : "tinted"
                                    implicitHeight: 30
                                    horizontalPadding: Theme.spacingSm
                                    font.pixelSize: Theme.sizeCaption
                                    onClicked: Power.setProfile(modelData)
                                }
                            }
                        }
                    }
                }

                // ── Media ────────────────────────────────────────────

                MediaPanel {
                    Layout.fillWidth: true
                    visible: Media.hasPlayer
                }

                // ── Capture and shortcuts ────────────────────────────

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingSm

                    GlassButton {
                        Layout.fillWidth: true
                        text: "Screenshot"
                        glyph: "󰹑"
                        onClicked: {
                            Overlays.close(root.name);
                            Actions.screenshot("region");
                        }
                    }

                    GlassButton {
                        Layout.fillWidth: true
                        text: "Record"
                        glyph: "󰑊"
                        destructive: false
                        onClicked: {
                            Overlays.close(root.name);
                            Actions.record("toggle");
                        }
                    }

                    GlassIconButton {
                        glyph: "󰒓"
                        tooltip: "Settings"
                        onClicked: {
                            Overlays.close(root.name);
                            Actions.openSettings("");
                        }
                    }

                    GlassIconButton {
                        glyph: "󰐥"
                        tooltip: "Power menu"
                        onClicked: Overlays.open("power", {})
                    }
                }

                // ── HyperNix ─────────────────────────────────────────

                HyperNixTile {
                    Layout.fillWidth: true
                    visible: HyperNix.enabled && Config.get("hypernix.showWidget", true)
                }
            }
        }
    }
}
