import QtQuick
import qs.Config
import qs.Services
import qs.Components
import "../"

/** Output volume: click to mute, scroll to change, right-click for the panel. */
BarItem {
    id: root

    property var hostBar: null

    readonly property int step: Config.get("bar.audio.scrollStep", 5)

    visible: Audio.ready
    tooltip: Audio.muted
        ? qsTr("Muted · %1").arg(Audio.sinkName)
        : qsTr("Volume %1% · %2").arg(Audio.volumePercent).arg(Audio.sinkName)

    onActivated: Actions.muteOutput()
    onSecondaryActivated: Actions.run(["shell", "control", "audio"])
    onScrolledUp: Actions.setVolume(Math.min(100, Audio.volumePercent + root.step))
    onScrolledDown: Actions.setVolume(Math.max(0, Audio.volumePercent - root.step))

    content: Row {
        spacing: Theme.spacingXs

        Icon {
            anchors.verticalCenter: parent.verticalCenter
            glyph: Audio.glyph
            size: Theme.sizeBody
            color: Audio.muted ? Theme.textTertiary : Theme.text
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            visible: !Audio.muted && Config.get("bar.audio.showPercent", true)
            text: Audio.volumePercent + "%"
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeFootnote
            font.features: ({ "tnum": 1 })
            renderType: Text.QtRendering
        }
    }
}
