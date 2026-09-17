import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.Config
import qs.Components
import qs.Services
import ".."

ColumnLayout {
    id: root
    spacing: Theme.spacingLg

    property var library: []
    property string current: ""

    Process {
        id: lister
        command: Paths.command(["wallpaper", "list"])
        running: true
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    root.library = JSON.parse(this.text) ?? [];
                } catch (error) {
                    root.library = [];
                }
            }
        }
    }

    Process {
        id: currentReader
        command: Paths.command(["wallpaper", "current"])
        running: true
        stdout: StdioCollector {
            onStreamFinished: root.current = this.text.trim()
        }
    }

    SettingsGroup {
        title: "Wallpaper"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingMd

            SettingRow {
                title: "Folder"
                description: "Where the rotation and the picker look."

                GlassField {
                    implicitWidth: 240
                    implicitHeight: 30
                    text: Config.get("wallpaper.rotation.directory", "")
                    onAccepted: value => {
                        Config.set("wallpaper.rotation.directory", value);
                        lister.running = true;
                    }
                }
            }

            SettingRow {
                title: "Fit"

                GlassSegmented {
                    options: ["fill", "fit", "stretch"]
                    value: Config.get("wallpaper.mode", "fill")
                    onSelected: value => Config.set("wallpaper.mode", value)
                }
            }

            SettingRow {
                title: "Derive colours"
                description: "The accent, surfaces and window borders all come from "
                    + "the wallpaper when this is on."

                GlassToggle {
                    checked: Config.get("wallpaper.deriveColors", true)
                    onToggled: value => Config.set("wallpaper.deriveColors", value)
                }
            }

            SettingRow {
                title: "Rotate"

                GlassToggle {
                    checked: Config.get("wallpaper.rotation.enabled", false)
                    onToggled: value => Config.set("wallpaper.rotation.enabled", value)
                }
            }

            GlassSetting {
                path: "wallpaper.rotation.intervalMinutes"
                title: "Every"
                from: 5; to: 480; step: 5; fallback: 30; integer: true; suffix: " min"
            }

            SettingRow {
                title: "Shuffle"

                GlassToggle {
                    checked: Config.get("wallpaper.rotation.shuffle", true)
                    onToggled: value => Config.set("wallpaper.rotation.shuffle", value)
                }
            }
        }
    }

    SettingsGroup {
        title: "Library"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingSm

            Label {
                Layout.fillWidth: true
                visible: root.library.length === 0
                text: "No images found. Set a folder above, or drop wallpapers into "
                    + "~/Pictures/Wallpapers."
                variant: "footnote"
                tone: "tertiary"
                wrapMode: Text.WordWrap
            }

            GridLayout {
                Layout.fillWidth: true
                columns: 4
                columnSpacing: Theme.spacingSm
                rowSpacing: Theme.spacingSm

                Repeater {
                    model: root.library.slice(0, 24)

                    Item {
                        required property var modelData

                        Layout.fillWidth: true
                        Layout.preferredHeight: 72

                        Rectangle {
                            anchors.fill: parent
                            radius: Theme.radiusSm
                            color: Theme.surfaceSunken
                            border.width: root.current === modelData ? 2 : 1
                            border.color: root.current === modelData
                                ? Theme.accent : Theme.glassBorder
                            clip: true

                            Image {
                                anchors.fill: parent
                                anchors.margins: 2
                                source: "file://" + modelData
                                fillMode: Image.PreserveAspectCrop
                                asynchronous: true
                                cache: true
                                sourceSize.width: 240
                            }
                        }

                        StateLayer {
                            anchors.fill: parent
                            radius: Theme.radiusSm
                            onClicked: {
                                Actions.run(["wallpaper", "set", modelData]);
                                root.current = modelData;
                            }
                        }
                    }
                }
            }

            RowLayout {
                spacing: Theme.spacingSm

                GlassButton {
                    text: "Next wallpaper"
                    glyph: "󰼨"
                    onClicked: {
                        Actions.wallpaperNext();
                        currentReader.running = true;
                    }
                }

                GlassButton {
                    text: "Rescan"
                    glyph: "󰑐"
                    onClicked: lister.running = true
                }
            }
        }
    }
}
