import QtQuick
import qs.Config
import qs.Services
import qs.Components
import "../"

/**
 * What is playing.
 *
 * Hidden when nothing is. Scroll changes track rather than volume:
 * a media module that changes volume surprises people who expected the
 * audio module to be the one that does that.
 */
BarItem {
    id: root

    property var hostBar: null

    readonly property int maximumWidth: Config.get("bar.media.maxWidth", 220)

    visible: Media.hasPlayer
    tooltip: Media.artist
        ? qsTr("%1 — %2").arg(Media.artist).arg(Media.title)
        : Media.title

    onActivated: Actions.media("play-pause")
    onSecondaryActivated: Actions.run(["shell", "control", "open"])
    onScrolledUp: if (Media.canGoNext) Actions.media("next")
    onScrolledDown: if (Media.canGoPrevious) Actions.media("previous")

    content: Row {
        spacing: Theme.spacingXs

        Icon {
            anchors.verticalCenter: parent.verticalCenter
            glyph: Media.playing ? "\udb81\udc0e" : "\udb81\udc0c"
            size: Theme.sizeBody
            color: Media.playing ? Theme.accent : Theme.textSecondary
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: Media.title
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeFootnote
            elide: Text.ElideRight
            width: Math.min(implicitWidth, root.maximumWidth)
            renderType: Text.QtRendering
        }
    }
}
