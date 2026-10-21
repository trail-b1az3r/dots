import QtQuick
import QtQuick.Layouts
import Qt5Compat.GraphicalEffects
import Quickshell.Services.Mpris
import qs
import qs.services
import qs.modules.common
import qs.modules.common.functions
import qs.modules.common.widgets
import qs.modules.ii.background.widgets

/**
 * What is playing: the cover, the title and artist, how far along it is, and the three transport buttons, on a card
 * in the theme's shape. The cover's frame, the progress line and the labels follow the theme (ThemeLook): an ember
 * edge and a lit line on Red Sun, facets on glass, a gold rail on Star Rail, keys on the anime themes. It is there
 * while a player is, and fades away when none is.
 */
AbstractBackgroundWidget {
    id: root

    configEntryName: "nowPlaying"

    readonly property var player: MprisController.activePlayer
    readonly property var track: MprisController.activeTrack
    readonly property ThemeLook look: ThemeLook {}

    implicitWidth: 380
    implicitHeight: 132
    opacity: (GlobalStates.screenLocked && !visibleWhenLocked) ? 0 : (player ? 1 : 0)

    // The position isn't pushed to us while a song plays.
    Timer {
        interval: 1000
        repeat: true
        running: root.visible && root.player?.playbackState === MprisPlaybackState.Playing
        onTriggered: root.player?.positionChanged()
    }

    ThemedPlate {
        anchors.fill: parent
        themeId: Config.options.halcyon.theme
        kind: "card"
        colBase: Appearance.colors.colLayer1
        colOn: Appearance.colors.colOnLayer1
        colAccent: Appearance.colors.colPrimary
    }

    RowLayout {
        anchors {
            fill: parent
            margins: 20
        }
        spacing: 16

        Rectangle {
            id: cover
            Layout.alignment: Qt.AlignVCenter
            implicitWidth: 92
            implicitHeight: 92
            radius: root.look.id === "glass" ? 4 : root.look.id === "keycap" ? 14 : Appearance.rounding.normal
            color: Appearance.colors.colLayer2
            border.width: root.look.id === "default" || root.look.id === "hyperneo" ? 0 : (root.look.id === "keycap" ? 2.5 : 1.5)
            border.color: root.look.id === "keycap" ? Qt.darker(root.look.card, 2.6) : root.look.glow

            StyledImage {
                id: art
                anchors.fill: parent
                source: root.track?.artUrl ?? ""
                fillMode: Image.PreserveAspectCrop
                layer.enabled: true
                layer.effect: OpacityMask {
                    maskSource: Rectangle {
                        width: cover.width
                        height: cover.height
                        radius: cover.radius
                    }
                }
            }
            MaterialSymbol {
                anchors.centerIn: parent
                visible: art.status !== Image.Ready
                text: "music_note"
                iconSize: 40
                color: Appearance.colors.colSubtext
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignVCenter
            spacing: 2

            StyledText {
                Layout.fillWidth: true
                text: StringUtils.cleanMusicTitle(root.track?.title ?? "")
                elide: Text.ElideRight
                font.pixelSize: Appearance.font.pixelSize.larger
                font.weight: root.look.id === "keycap" ? Font.Bold : Font.Medium
                color: root.look.text
                style: root.look.id === "red-sun" ? Text.Raised : Text.Normal
                styleColor: root.look.glow
            }
            StyledText {
                Layout.fillWidth: true
                text: root.look.label(root.track?.artist ?? "")
                elide: Text.ElideRight
                font.pixelSize: Appearance.font.pixelSize.small
                font.letterSpacing: root.look.spacing
                color: root.look.subtext
            }

            // How far along it is.
            ThemedProgress {
                Layout.fillWidth: true
                Layout.topMargin: 8
                look: root.look
                value: root.player && root.player.length > 0 ? root.player.position / root.player.length : 0
            }

            RowLayout {
                Layout.topMargin: 2
                spacing: 6

                Repeater {
                    model: [
                        { icon: "skip_previous", enabled: MprisController.canGoPrevious, act: () => MprisController.previous() },
                        { icon: MprisController.isPlaying ? "pause" : "play_arrow", enabled: MprisController.canTogglePlaying, act: () => MprisController.togglePlaying() },
                        { icon: "skip_next", enabled: MprisController.canGoNext, act: () => MprisController.next() }
                    ]

                    delegate: MouseArea {
                        id: control
                        required property var modelData
                        implicitWidth: 34
                        implicitHeight: 30
                        enabled: modelData.enabled
                        cursorShape: Qt.PointingHandCursor
                        hoverEnabled: true
                        onClicked: modelData.act()

                        Rectangle {
                            anchors.fill: parent
                            radius: Appearance.rounding.small
                            color: control.containsMouse ? Appearance.colors.colLayer2Hover : "transparent"
                        }
                        MaterialSymbol {
                            anchors.centerIn: parent
                            text: control.modelData.icon
                            iconSize: 24
                            fill: 1
                            color: control.enabled ? root.look.text : root.look.subtext
                        }
                    }
                }
            }
        }
    }
}
