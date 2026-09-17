import QtQuick
import QtQuick.Layouts
import qs.Config
import qs.Components
import ".."

ColumnLayout {
    spacing: Theme.spacingLg

    SettingsGroup {
        title: "Motion"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingMd

            SettingRow {
                title: "Preset"
                description: "Minimal is shortest, Smooth is longest, Disabled turns "
                    + "animations off in the shell and the compositor alike."

                GlassSegmented {
                    options: ["minimal", "macos", "smooth", "fast", "disabled"]
                    value: Config.get("motion.preset", "macos")
                    onSelected: value => Config.set("motion.preset", value)
                }
            }

            GlassSetting {
                path: "motion.speedScale"
                title: "Speed"
                prose: "Scales every duration. Higher is slower."
                from: 0.3; to: 2.0; step: 0.05; fallback: 1.0
            }

            SettingRow {
                title: "Reduced motion"
                description: "Shortens and flattens animations, and stops anything "
                    + "that spins or slides a long way."

                GlassToggle {
                    checked: Config.get("motion.reducedMotion", false)
                    onToggled: value => Config.set("motion.reducedMotion", value)
                }
            }

            SettingRow {
                title: "Overlay animations"
                description: "Fade and scale for Spotlight, Control Center and the rest."

                GlassToggle {
                    checked: Config.get("motion.overlayAnimations", true)
                    onToggled: value => Config.set("motion.overlayAnimations", value)
                }
            }
        }
    }

    SettingsGroup {
        title: "What this changes"

        Label {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            text: "Halcyon generates Hyprland's animation configuration from these "
                + "values, so window, workspace and layer animations move on the same "
                + "curves as the shell's own panels. The continuously-animating "
                + "gradient effects (border, shadow and glow angle) stay off: they "
                + "redraw every frame for as long as a window is open, which is a "
                + "measurable amount of battery for an effect most people never notice."
            variant: "footnote"
            tone: "secondary"
            wrapMode: Text.WordWrap
        }
    }
}
