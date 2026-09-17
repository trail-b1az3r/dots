import QtQuick
import QtQuick.Layouts
import qs.Config
import qs.Components
import qs.Services
import ".."

ColumnLayout {
    id: root
    spacing: Theme.spacingLg

    readonly property var tiers: ["off", "low", "medium", "high", "ultra"]

    SettingsGroup {
        title: "Rendering"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingMd

            SettingRow {
                title: "Blur quality"
                description: "Sample distance and passes. Each step roughly doubles "
                    + "what the GPU does behind every translucent surface."

                GlassSegmented {
                    options: root.tiers
                    value: Config.get("graphics.blurQuality", "high")
                    onSelected: value => Config.set("graphics.blurQuality", value)
                }
            }

            SettingRow {
                title: "Shadow quality"

                GlassSegmented {
                    options: root.tiers
                    value: Config.get("graphics.shadowQuality", "high")
                    onSelected: value => Config.set("graphics.shadowQuality", value)
                }
            }

            SettingRow {
                title: "Animation quality"

                GlassSegmented {
                    options: ["low", "medium", "high"]
                    value: Config.get("graphics.animationQuality", "high")
                    onSelected: value => Config.set("graphics.animationQuality", value)
                }
            }

            GlassSetting {
                path: "graphics.transparency"
                title: "Transparency"
                prose: "Scales every surface toward solid. 1.0 keeps the preset."
                from: 0.0; to: 1.0; step: 0.05; fallback: 1.0
            }

            SettingRow {
                title: "Low Power Graphics"
                description: "Clamps blur and shadows, and switches off the "
                    + "decorative layers — highlights, grain and refraction."

                GlassToggle {
                    checked: Config.get("graphics.lowPowerGraphics", false)
                    onToggled: value => Config.set("graphics.lowPowerGraphics", value)
                }
            }

            GlassSetting {
                path: "graphics.renderUnfocusedFps"
                title: "Unfocused frame rate"
                prose: "Frames per second for windows that asked to keep rendering "
                    + "while they are not focused, such as a video call."
                from: 1; to: 60; step: 1; fallback: 10; integer: true; suffix: " fps"
            }
        }
    }

    SettingsGroup {
        title: "This machine"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingXs

            Label {
                Layout.fillWidth: true
                text: "Blur is currently " + (Theme.blurEnabled ? "on" : "off")
                    + " at the " + Theme.quality.blur + " tier."
                variant: "footnote"
                tone: "secondary"
            }

            Label {
                Layout.fillWidth: true
                visible: Object.keys(Power.policy).length > 0
                text: "Adaptive policy: " + (Power.policy.reason ?? "")
                variant: "footnote"
                tone: "tertiary"
            }
        }
    }
}
