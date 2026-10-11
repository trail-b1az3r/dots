import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.Config
import qs.Components
import qs.Services
import ".."

/**
 * Desktop widgets, and the Star Rail theme's characters.
 *
 * Everything here is off until switched on. The Star Rail section is the
 * only place that fetches anything from the network, and it says so: the
 * fetch toggle, and the two buttons that download, are the only paths.
 */
ColumnLayout {
    id: root
    spacing: Theme.spacingLg

    property var starRail: ({ current: null, characters: 0 })

    Process {
        id: starRailProbe
        command: Paths.command(["starrail", "status", "--json"])
        running: true
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    root.starRail = JSON.parse(this.text) ?? { current: null, characters: 0 };
                } catch (error) {
                    root.starRail = { current: null, characters: 0 };
                }
            }
        }
    }

    SettingsGroup {
        title: "Revolver"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingMd

            SettingRow {
                title: "Show the revolver on the desktop"
                description: "A drum of your installed games. Drag to spin, release, then click the centre to start the chamber under the pin. Off by default."

                GlassToggle {
                    checked: Config.get("widgets.revolver.enabled", false)
                    onToggled: value => Config.set("widgets.revolver.enabled", value)
                }
            }

            SettingRow {
                title: "Games come from"
                description: "Read from local files only. Nothing is uploaded."

                GlassSegmented {
                    options: [
                        { value: "steam", title: "Steam" },
                        { value: "prismlauncher", title: "PrismLauncher" }
                    ]
                    value: Config.get("widgets.revolver.source", "steam")
                    onSelected: value => Config.set("widgets.revolver.source", value)
                }
            }

            SettingRow {
                title: "Weighting"
                description: "Recent favours what you played lately. Random ignores history. Recommended favours recent games and ones left untouched for a while."

                GlassSegmented {
                    options: [
                        { value: "recent", title: "Recent" },
                        { value: "random", title: "Random" },
                        { value: "recommended", title: "Recommended" }
                    ]
                    value: Config.get("widgets.revolver.mode", "recent")
                    onSelected: value => Config.set("widgets.revolver.mode", value)
                }
            }
        }
    }

    SettingsGroup {
        title: "Star Rail theme"

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: Theme.spacingMd

            SettingRow {
                title: "Refresh the character list automatically"
                description: "Off by default. When on, the public character index is refreshed about once a week. Turning it off stops that; the buttons below still work."

                GlassToggle {
                    checked: Config.get("starRail.fetchCharacters", false)
                    onToggled: value => Config.set("starRail.fetchCharacters", value)
                }
            }

            SettingRow {
                title: "Take the element's colour as the accent"
                description: "Each element has its own colour. When this is on, showing a character also sets the accent to match."

                GlassToggle {
                    checked: Config.get("starRail.accentFromCharacter", false)
                    onToggled: value => Config.set("starRail.accentFromCharacter", value)
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spacingMd

                Image {
                    visible: status === Image.Ready
                    source: root.starRail.current ? "file://" + root.starRail.current.portrait : ""
                    Layout.preferredWidth: 72
                    Layout.preferredHeight: 72
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                    asynchronous: true
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingXs

                    Text {
                        text: root.starRail.current
                            ? root.starRail.current.name + " · " + root.starRail.current.element + " · " + root.starRail.current.path
                            : "No character chosen yet."
                        color: Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sizeBody
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                        renderType: Text.QtRendering
                    }

                    Text {
                        text: root.starRail.characters + " characters in the cache"
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.sizeCaption
                        renderType: Text.QtRendering
                    }

                    RowLayout {
                        spacing: Theme.spacingSm

                        GlassButton {
                            text: "Show another character"
                            onClicked: {
                                Actions.run(["action", "starrail.next"]);
                                starRailProbe.running = true;
                            }
                        }

                        GlassButton {
                            text: "Refresh the list"
                            variant: "plain"
                            onClicked: {
                                Actions.run(["action", "starrail.refresh"]);
                                starRailProbe.running = true;
                            }
                        }
                    }
                }
            }
        }
    }
}
