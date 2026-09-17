import QtQuick
import QtQuick.Layouts
import Quickshell.Services.Pipewire
import qs.Config
import qs.Components
import qs.Services
import ".."

ColumnLayout {
    spacing: Theme.spacingLg

    SettingsGroup {
        title: "Output"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingMd

            SettingRow {
                title: "Volume"
                description: Audio.muted ? "Muted" : Audio.volumePercent + "%"

                GlassSlider {
                    implicitWidth: 200
                    glyph: Audio.glyph
                    value: Audio.volume
                    onMoved: value => Audio.setVolume(value)
                }
            }

            Label {
                Layout.fillWidth: true
                visible: Audio.sinks.length > 0
                text: "Devices"
                variant: "caption"
                tone: "tertiary"
            }

            Repeater {
                model: Audio.sinks

                ListRow {
                    required property var modelData
                    Layout.fillWidth: true
                    implicitHeight: 38
                    title: modelData.nickname ?? modelData.description ?? modelData.name
                    glyph: "󰓃"
                    iconSize: 16
                    selected: Audio.sink === modelData
                    onActivated: Audio.setDefaultSink(modelData)
                }
            }
        }
    }

    SettingsGroup {
        title: "Input"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingMd

            SettingRow {
                title: "Microphone"
                description: Audio.inputMuted ? "Muted" : Audio.sourceName

                GlassToggle {
                    checked: !Audio.inputMuted
                    onToggled: Audio.toggleInputMute()
                }
            }

            SettingRow {
                title: "Input level"

                GlassSlider {
                    implicitWidth: 200
                    glyph: Audio.inputGlyph
                    value: Audio.inputVolume
                    onMoved: value => Audio.setInputVolume(value)
                }
            }
        }
    }

    SettingsGroup {
        title: "Playing now"
        visible: Audio.streams.length > 0

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingSm

            Repeater {
                model: Audio.streams

                RowLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    spacing: Theme.spacingMd

                    Label {
                        Layout.preferredWidth: 130
                        text: modelData.properties["application.name"]
                            ?? modelData.description ?? modelData.name
                        variant: "footnote"
                        elide: Text.ElideRight
                    }

                    GlassSlider {
                        Layout.fillWidth: true
                        implicitHeight: 22
                        value: modelData.audio?.volume ?? 0
                        onMoved: value => {
                            if (modelData.audio)
                                modelData.audio.volume = value;
                        }
                    }
                }
            }

            PwObjectTracker { objects: Audio.streams }
        }
    }
}
