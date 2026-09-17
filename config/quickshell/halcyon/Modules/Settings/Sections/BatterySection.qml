import QtQuick
import QtQuick.Layouts
import qs.Config
import qs.Components
import qs.Services
import ".."

ColumnLayout {
    spacing: Theme.spacingLg

    SettingsGroup {
        title: "Status"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingXs

            Label {
                Layout.fillWidth: true
                text: Power.hasBattery
                    ? Power.percent + "%  ·  " + Power.remaining
                    : "This machine has no battery."
                variant: "body"
            }

            Label {
                Layout.fillWidth: true
                visible: Power.hasBattery && Power.healthKnown
                text: "Health: " + Math.round(Power.health) + "% of the original capacity"
                variant: "footnote"
                tone: "tertiary"
            }

            Label {
                Layout.fillWidth: true
                visible: Power.changeRate > 0
                text: "Drawing " + Power.changeRate.toFixed(1) + " W"
                variant: "footnote"
                tone: "tertiary"
            }
        }
    }

    SettingsGroup {
        title: "Power profile"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingMd

            SettingRow {
                title: "Profile"
                description: "Driven through whichever of power-profiles-daemon, "
                    + "TLP or tuned is installed — never more than one at a time."

                GlassSegmented {
                    options: [
                        { value: "performance", title: "Performance" },
                        { value: "balanced", title: "Balanced" },
                        { value: "battery-saver", title: "Saver" }
                    ]
                    value: Power.profile
                    onSelected: value => Power.setProfile(value)
                }
            }
        }
    }

    SettingsGroup {
        title: "Adaptive effects"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingMd

            SettingRow {
                title: "Reduce effects on battery"
                description: "Steps blur and shadows down as the charge falls. Your "
                    + "chosen settings are never overwritten — the policy is applied "
                    + "on top of them and lifts when you plug in."

                GlassToggle {
                    checked: Config.get("power.adaptive.reduceEffectsOnBattery", true)
                    onToggled: value => Config.set("power.adaptive.reduceEffectsOnBattery", value)
                }
            }

            GlassSetting {
                path: "power.adaptive.batteryThreshold"
                title: "Reduce below"
                from: 5; to: 90; step: 5; fallback: 25; integer: true; suffix: "%"
            }

            GlassSetting {
                path: "power.adaptive.criticalThreshold"
                title: "Critical below"
                prose: "Blur and shadows off, animations minimal, saver profile."
                from: 2; to: 30; step: 1; fallback: 10; integer: true; suffix: "%"
            }
        }
    }

    SettingsGroup {
        title: "Idle"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingMd

            SettingRow {
                title: "Idle handling"
                description: "Dim, blank, lock and sleep on a timer."

                GlassToggle {
                    checked: Config.get("power.idle.enabled", true)
                    onToggled: value => Config.set("power.idle.enabled", value)
                }
            }

            GlassSetting {
                path: "power.idle.acDimSeconds"
                title: "Dim (on AC)"
                from: 30; to: 3600; step: 30; fallback: 600; integer: true; suffix: " s"
            }

            GlassSetting {
                path: "power.idle.acScreenOffSeconds"
                title: "Screen off (on AC)"
                from: 60; to: 7200; step: 60; fallback: 900; integer: true; suffix: " s"
            }

            GlassSetting {
                path: "power.idle.batteryDimSeconds"
                title: "Dim (on battery)"
                from: 15; to: 1800; step: 15; fallback: 150; integer: true; suffix: " s"
            }

            GlassSetting {
                path: "power.idle.batteryScreenOffSeconds"
                title: "Screen off (on battery)"
                from: 30; to: 3600; step: 30; fallback: 300; integer: true; suffix: " s"
            }

            GlassSetting {
                path: "power.idle.batterySuspendSeconds"
                title: "Sleep (on battery)"
                prose: "0 never sleeps."
                from: 0; to: 7200; step: 60; fallback: 900; integer: true; suffix: " s"
            }
        }
    }
}
