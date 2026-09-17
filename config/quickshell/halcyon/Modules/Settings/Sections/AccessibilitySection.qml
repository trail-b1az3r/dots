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
                title: "Reduced motion"
                description: "Shortens animations and stops anything that spins, "
                    + "slides a long way, or overshoots."

                GlassToggle {
                    checked: Config.get("accessibility.reducedMotion", false)
                    onToggled: value => Config.set("accessibility.reducedMotion", value)
                }
            }

            SettingRow {
                title: "Disable animations"
                description: "Everything changes instantly, in the shell and the "
                    + "compositor."

                GlassToggle {
                    checked: Config.get("accessibility.disableAnimations", false)
                    onToggled: value => Config.set("accessibility.disableAnimations", value)
                }
            }
        }
    }

    SettingsGroup {
        title: "Legibility"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingMd

            SettingRow {
                title: "High contrast"
                description: "Solid surfaces, strong borders, and text held to a "
                    + "7:1 contrast ratio."

                GlassToggle {
                    checked: Config.get("accessibility.highContrast", false)
                    onToggled: value => Config.set("accessibility.highContrast", value)
                }
            }

            SettingRow {
                title: "Disable blur"
                description: "Panels become opaque — translucency without blur is "
                    + "unreadable, so this raises opacity too."

                GlassToggle {
                    checked: Config.get("accessibility.disableBlur", false)
                    onToggled: value => Config.set("accessibility.disableBlur", value)
                }
            }

            SettingRow {
                title: "Larger text"

                GlassToggle {
                    checked: Config.get("accessibility.largeText", false)
                    onToggled: value => Config.set("accessibility.largeText", value)
                }
            }

            GlassSetting {
                path: "accessibility.textScale"
                title: "Text scale"
                from: 0.8; to: 2.0; step: 0.05; fallback: 1.0
            }

            GlassSetting {
                path: "accessibility.minimumTransparency"
                title: "Minimum opacity"
                prose: "A floor no preset can go below."
                from: 0.0; to: 1.0; step: 0.05; fallback: 0.0
            }

            SettingRow {
                title: "Focus ring"
                description: "A visible outline on whatever has keyboard focus."

                GlassToggle {
                    checked: Config.get("accessibility.focusRing", true)
                    onToggled: value => Config.set("accessibility.focusRing", value)
                }
            }

            SettingRow {
                title: "Screen reader labels"
                description: "Name and describe every control for assistive technology."

                GlassToggle {
                    checked: Config.get("accessibility.screenReaderLabels", true)
                    onToggled: value => Config.set("accessibility.screenReaderLabels", value)
                }
            }
        }
    }
}
