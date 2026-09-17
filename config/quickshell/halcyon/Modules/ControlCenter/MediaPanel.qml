import QtQuick
import QtQuick.Layouts
import qs.Config
import qs.Components
import qs.Services

/**
 * Now Playing.
 *
 * Album art, title, artist, transport and a scrubber. The art is the
 * panel's own backdrop at low opacity, which is both the nicest-looking
 * option and free: the image is already decoded.
 */
GlassSurface {
    id: root

    level: 1
    radius: Theme.radiusLg
    padding: Theme.panelPaddingTight
    implicitHeight: layout.implicitHeight + padding * 2
    clipContent: true

    // The art, blurred behind the controls. Kept very faint so the text
    // over it stays at full contrast.
    Image {
        anchors.fill: parent
        source: Media.artUrl
        visible: Media.artUrl.length > 0 && Theme.decorativeEffects
        fillMode: Image.PreserveAspectCrop
        opacity: 0.16
        asynchronous: true
        cache: true
        z: -1
    }

    ColumnLayout {
        id: layout
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: Theme.spacingSm

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacingMd

            Rectangle {
                Layout.preferredWidth: 52
                Layout.preferredHeight: 52
                radius: Theme.radiusSm
                color: Theme.surfaceSunken
                clip: true

                Image {
                    anchors.fill: parent
                    source: Media.artUrl
                    visible: Media.artUrl.length > 0
                    fillMode: Image.PreserveAspectCrop
                    asynchronous: true
                    cache: true
                }

                Icon {
                    anchors.centerIn: parent
                    visible: Media.artUrl.length === 0
                    glyph: "󰝚"
                    size: 22
                    color: Theme.textTertiary
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 1

                Label {
                    Layout.fillWidth: true
                    text: Media.title.length > 0 ? Media.title : "Nothing playing"
                    variant: "body"
                    font.weight: Theme.weightMedium
                }

                Label {
                    Layout.fillWidth: true
                    visible: Media.artist.length > 0
                    text: Media.artist
                    variant: "footnote"
                    tone: "secondary"
                }

                Label {
                    Layout.fillWidth: true
                    visible: Media.identity.length > 0
                    text: Media.identity
                    variant: "caption"
                    tone: "tertiary"
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacingXs

            GlassIconButton {
                glyph: "󰒮"
                enabled: Media.canGoPrevious
                tooltip: "Previous"
                onClicked: Media.previous()
            }

            GlassIconButton {
                glyph: Media.statusGlyph
                size: 38
                iconSize: 18
                tooltip: Media.playing ? "Pause" : "Play"
                onClicked: Media.playPause()
            }

            GlassIconButton {
                glyph: "󰒭"
                enabled: Media.canGoNext
                tooltip: "Next"
                onClicked: Media.next()
            }

            Item { Layout.fillWidth: true }

            GlassIconButton {
                glyph: "󰏋"
                tooltip: "Show the player"
                onClicked: Media.raise()
            }
        }

        GlassSlider {
            Layout.fillWidth: true
            implicitHeight: 6
            visible: Media.canSeek && Media.length > 0
            value: Media.length > 0 ? Media.position / Media.length : 0
            onCommitted: value => Media.seek(value)
        }
    }
}
