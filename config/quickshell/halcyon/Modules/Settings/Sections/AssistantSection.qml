import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.Config
import qs.Components
import qs.Services
import ".."

/**
 * The AI assistant's settings, including the provider switch.
 *
 * Both backends are listed with their real health, read from the daemon,
 * so "NixOrb" is not an option that silently does nothing when NixOrb is
 * not installed.
 */
ColumnLayout {
    id: root
    spacing: Theme.spacingLg

    property var providers: []

    Process {
        id: probe
        command: Paths.command(["assistant", "providers", "--json"])
        running: true
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    root.providers = JSON.parse(this.text) ?? [];
                } catch (error) {
                    root.providers = [];
                }
            }
        }
    }

    SettingsGroup {
        title: "Assistant"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingMd

            SettingRow {
                title: "Enabled"
                description: "Turning this off removes the orb, the bar indicator "
                    + "and the Spotlight entry. Nothing else changes."

                GlassToggle {
                    checked: Config.get("assistant.enabled", true)
                    onToggled: value => Config.set("assistant.enabled", value)
                }
            }

            SettingRow {
                title: "Provider"
                description: "Automatic prefers NixOrb while it is running, because "
                    + "it owns the microphone and its own interface; otherwise the "
                    + "local stack answers."

                GlassSegmented {
                    options: [
                        { value: "nixorb", title: "NixOrb" },
                        { value: "local", title: "Local AI" },
                        { value: "auto", title: "Automatic" }
                    ]
                    value: Config.get("assistant.provider", "auto")
                    onSelected: value => {
                        Config.set("assistant.provider", value);
                        probe.running = true;
                    }
                }
            }
        }
    }

    SettingsGroup {
        title: "Backends"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingSm

            Repeater {
                model: root.providers

                RowLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    spacing: Theme.spacingSm

                    Icon {
                        Layout.alignment: Qt.AlignTop
                        glyph: modelData.ok ? "󰄬" : "󰅖"
                        size: 14
                        color: modelData.ok ? Theme.success : Theme.textTertiary
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 0

                        Label {
                            Layout.fillWidth: true
                            text: modelData.title
                            variant: "body"
                        }

                        Label {
                            Layout.fillWidth: true
                            text: modelData.status
                            variant: "caption"
                            tone: "tertiary"
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }

            GlassButton {
                Layout.alignment: Qt.AlignLeft
                text: "Re-check"
                glyph: "󰑐"
                onClicked: probe.running = true
            }
        }
    }

    SettingsGroup {
        title: "Voice"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingMd

            SettingRow {
                title: "Speak replies"

                GlassToggle {
                    checked: Config.get("assistant.voice.enabled", true)
                    onToggled: value => Config.set("assistant.voice.enabled", value)
                }
            }

            SettingRow {
                title: "Voice"
                description: "A Piper voice name, or a path to a .onnx model."

                GlassField {
                    implicitWidth: 220
                    implicitHeight: 30
                    text: Config.get("assistant.voice.name", "")
                    onAccepted: value => Config.set("assistant.voice.name", value)
                }
            }

            GlassSetting {
                path: "assistant.voice.speed"
                title: "Speaking speed"
                from: 0.5; to: 2.0; step: 0.05; fallback: 1.0
            }

            SettingRow {
                title: "Push to talk only"
                description: "Never listens unless you hold the shortcut."

                GlassToggle {
                    checked: Config.get("assistant.pushToTalkOnly", false)
                    onToggled: value => Config.set("assistant.pushToTalkOnly", value)
                }
            }

            SettingRow {
                title: "Wake word"
                description: "Off by default. A wake word means the microphone is "
                    + "open whenever the assistant is running."

                GlassToggle {
                    checked: Config.get("assistant.wakeWord.enabled", false)
                    onToggled: value => Config.set("assistant.wakeWord.enabled", value)
                }
            }

            SettingRow {
                title: "Respect microphone mute"
                description: "Refuse to record while the input is muted, instead of "
                    + "recording silence and reporting that it heard nothing."

                GlassToggle {
                    checked: Config.get("assistant.microphone.respectMute", true)
                    onToggled: value => Config.set("assistant.microphone.respectMute", value)
                }
            }
        }
    }

    SettingsGroup {
        title: "Local AI"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingMd

            SettingRow {
                title: "Language model backend"

                GlassSegmented {
                    options: [
                        { value: "ollama", title: "Ollama" },
                        { value: "openai-compatible", title: "OpenAI API" },
                        { value: "none", title: "None" }
                    ]
                    value: Config.get("assistant.local.llmBackend", "ollama")
                    onSelected: value => Config.set("assistant.local.llmBackend", value)
                }
            }

            SettingRow {
                title: "Host"

                GlassField {
                    implicitWidth: 240
                    implicitHeight: 30
                    text: Config.get("assistant.local.llmHost", "http://127.0.0.1:11434")
                    onAccepted: value => Config.set("assistant.local.llmHost", value)
                }
            }

            SettingRow {
                title: "Model"

                GlassField {
                    implicitWidth: 240
                    implicitHeight: 30
                    text: Config.get("assistant.local.llmModel", "llama3.2:3b")
                    onAccepted: value => Config.set("assistant.local.llmModel", value)
                }
            }

            SettingRow {
                title: "Speech to text"

                GlassSegmented {
                    options: [
                        { value: "whisper-cpp", title: "whisper.cpp" },
                        { value: "faster-whisper", title: "faster-whisper" }
                    ]
                    value: Config.get("assistant.local.sttBackend", "whisper-cpp")
                    onSelected: value => Config.set("assistant.local.sttBackend", value)
                }
            }
        }
    }

    SettingsGroup {
        title: "Privacy"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingMd

            Label {
                Layout.fillWidth: true
                text: "Nothing leaves this machine unless you switch it on here. "
                    + "Audio is recorded only while a turn is running, transcribed "
                    + "locally, and the recording is deleted immediately afterwards."
                variant: "caption"
                tone: "tertiary"
                wrapMode: Text.WordWrap
            }

            SettingRow {
                title: "Allow web access"
                description: "Lets the assistant open searches and fetch exchange rates."

                GlassToggle {
                    checked: Config.get("assistant.privacy.allowWebAccess", false)
                    onToggled: value => Config.set("assistant.privacy.allowWebAccess", value)
                }
            }

            SettingRow {
                title: "Allow screen context"
                description: "Lets the assistant see what is on screen when you ask "
                    + "about it. Off by default."

                GlassToggle {
                    checked: Config.get("assistant.privacy.allowScreenContext", false)
                    onToggled: value => Config.set("assistant.privacy.allowScreenContext", value)
                }
            }

            SettingRow {
                title: "Store conversations"
                description: "Keeps the transcript on disk so context survives a restart."

                GlassToggle {
                    checked: Config.get("assistant.privacy.storeConversations", true)
                    onToggled: value => Config.set("assistant.privacy.storeConversations", value)
                }
            }

            SettingRow {
                title: "Confirm destructive actions"
                description: "Always ask before logging out, restarting or shutting down."

                GlassToggle {
                    checked: Config.get("assistant.privacy.confirmDestructiveActions", true)
                    onToggled: value => Config.set(
                        "assistant.privacy.confirmDestructiveActions", value
                    )
                }
            }
        }
    }
}
