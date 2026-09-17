import QtQuick
import QtQuick.Layouts
import qs.Config
import qs.Components
import qs.Services
import ".."

ColumnLayout {
    spacing: Theme.spacingLg

    SettingsGroup {
        title: "Mode"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingMd

            SettingRow {
                title: "Appearance"
                description: "Automatic follows the wallpaper's brightness."

                GlassSegmented {
                    options: ["light", "dark", "auto"]
                    value: Config.get("appearance.mode", "dark")
                    onSelected: value => Config.set("appearance.mode", value)
                }
            }

            SettingRow {
                title: "Accent colour"
                description: "Derived from the wallpaper, or fixed to one colour."

                GlassSegmented {
                    options: [
                        { value: "wallpaper", title: "Wallpaper" },
                        { value: "fixed", title: "Fixed" }
                    ]
                    value: Config.get("appearance.accentSource", "wallpaper")
                    onSelected: value => Config.set("appearance.accentSource", value)
                }
            }

            SettingRow {
                title: "Fixed accent"
                description: Config.get("appearance.accentColor", "#0A84FF")
                visible: Config.get("appearance.accentSource", "wallpaper") === "fixed"

                Rectangle {
                    width: 60
                    height: 26
                    radius: Theme.radiusXs
                    color: Config.get("appearance.accentColor", "#0A84FF")
                    border.width: 1
                    border.color: Theme.glassBorder
                }
            }

            SettingRow {
                title: "Corner style"
                description: "Continuous corners ease into the edge, like a squircle."

                GlassSegmented {
                    options: [
                        { value: "continuous", title: "Continuous" },
                        { value: "circular", title: "Circular" }
                    ]
                    value: Config.get("appearance.cornerStyle", "continuous")
                    onSelected: value => Config.set("appearance.cornerStyle", value)
                }
            }
        }
    }

    SettingsGroup {
        title: "Typography"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingMd

            SettingRow {
                title: "Interface font"

                GlassField {
                    implicitWidth: 200
                    implicitHeight: 30
                    text: Config.get("appearance.fontUi", "Inter")
                    onAccepted: value => Config.set("appearance.fontUi", value)
                }
            }

            SettingRow {
                title: "Monospace font"

                GlassField {
                    implicitWidth: 200
                    implicitHeight: 30
                    text: Config.get("appearance.fontMono", "JetBrains Mono")
                    onAccepted: value => Config.set("appearance.fontMono", value)
                }
            }

            SettingRow {
                title: "Text size"
                description: Math.round(Config.get("appearance.fontSizeScale", 1.0) * 100) + "%"

                GlassSlider {
                    implicitWidth: 180
                    from: 0.8
                    to: 1.5
                    step: 0.05
                    value: Config.get("appearance.fontSizeScale", 1.0)
                    onCommitted: value => Config.set("appearance.fontSizeScale", value)
                }
            }
        }
    }

    SettingsGroup {
        title: "Cursor and icons"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingMd

            SettingRow {
                title: "Icon theme"

                GlassField {
                    implicitWidth: 200
                    implicitHeight: 30
                    text: Config.get("appearance.iconTheme", "Papirus-Dark")
                    onAccepted: value => Config.set("appearance.iconTheme", value)
                }
            }

            SettingRow {
                title: "Cursor theme"

                GlassField {
                    implicitWidth: 200
                    implicitHeight: 30
                    text: Config.get("appearance.cursorTheme", "")
                    onAccepted: value => Config.set("appearance.cursorTheme", value)
                }
            }

            SettingRow {
                title: "Cursor size"
                description: Config.get("appearance.cursorSize", 24) + " px"

                GlassSlider {
                    implicitWidth: 180
                    from: 16
                    to: 64
                    step: 4
                    value: Config.get("appearance.cursorSize", 24)
                    onCommitted: value => Config.set("appearance.cursorSize", Math.round(value))
                }
            }
        }
    }
}
