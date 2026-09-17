import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.Config
import qs.Components
import qs.Services
import ".."

/**
 * About, and the diagnostics people actually need when reporting a
 * problem: versions, what is running, and the output of `halcyon doctor`
 * without having to open a terminal.
 */
ColumnLayout {
    id: root
    spacing: Theme.spacingLg

    property var report: ({})
    property bool running: false

    function check(): void {
        root.running = true;
        doctor.running = true;
    }

    Process {
        id: doctor
        command: Paths.command(["doctor", "--json"])
        running: true
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    root.report = JSON.parse(this.text) ?? ({});
                } catch (error) {
                    root.report = ({});
                }
                root.running = false;
            }
        }
        onExited: root.running = false
    }

    SettingsGroup {
        title: "Halcyon"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingXs

            Label {
                Layout.fillWidth: true
                text: "Halcyon " + (root.report.version ?? "")
                variant: "title"
            }

            Label {
                Layout.fillWidth: true
                text: "A Liquid-Glass-inspired desktop environment for Hyprland."
                variant: "footnote"
                tone: "secondary"
            }

            Label {
                Layout.fillWidth: true
                text: "Palette: " + (Theme.palette.source ?? "fallback")
                    + "  ·  accent " + (Theme.palette.accent ?? "")
                    + "  ·  " + Theme.mode + " mode"
                variant: "caption"
                tone: "tertiary"
            }

            Label {
                Layout.fillWidth: true
                text: "Settings: " + Paths.settingsFile
                variant: "caption"
                tone: "tertiary"
            }
        }
    }

    SettingsGroup {
        title: "Diagnostics"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingSm

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spacingSm

                Label {
                    Layout.fillWidth: true
                    text: root.running
                        ? "Checking…"
                        : (root.report.ok
                            ? "Everything essential is working."
                            : "Some checks need attention.")
                    variant: "body"
                    color: root.report.ok === false ? Theme.warning : Theme.text
                }

                Spinner { visible: root.running; size: 14 }

                GlassButton {
                    text: "Re-check"
                    glyph: "󰑐"
                    onClicked: root.check()
                }
            }

            Repeater {
                model: root.report.checks ?? []

                RowLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    spacing: Theme.spacingSm

                    Icon {
                        Layout.alignment: Qt.AlignTop
                        glyph: modelData.ok ? "󰄬" : (modelData.severity === "error" ? "󰅖" : "󰀦")
                        size: 13
                        color: modelData.ok
                            ? Theme.success
                            : (modelData.severity === "error" ? Theme.danger : Theme.warning)
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 0

                        Label {
                            Layout.fillWidth: true
                            text: modelData.name
                            variant: "footnote"
                        }

                        Label {
                            Layout.fillWidth: true
                            visible: String(modelData.detail ?? "").length > 0
                            text: modelData.detail
                            variant: "caption"
                            tone: "tertiary"
                            wrapMode: Text.WordWrap
                        }

                        Label {
                            Layout.fillWidth: true
                            visible: String(modelData.fix ?? "").length > 0
                            text: "→ " + modelData.fix
                            variant: "caption"
                            color: Theme.accentText
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }
        }
    }

    SettingsGroup {
        title: "Configuration"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingSm

            Label {
                Layout.fillWidth: true
                text: "Backups of whatever was in place before Halcyon are kept in "
                    + Paths.stateHome + "/halcyon/backups, newest linked as "
                    + "\"latest\". ./restore.sh puts any of them back."
                variant: "footnote"
                tone: "secondary"
                wrapMode: Text.WordWrap
            }

            RowLayout {
                spacing: Theme.spacingSm

                GlassButton {
                    text: "Regenerate theme"
                    glyph: "󰑐"
                    onClicked: Actions.run(["theme", "apply"])
                }

                GlassButton {
                    text: "Reload the desktop"
                    glyph: "󰜉"
                    onClicked: Actions.run(["session", "reload"])
                }
            }
        }
    }
}
