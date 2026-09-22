import QtQuick
import qs.Config
import qs.Services
import qs.Components
import "../"

/**
 * Input mute state.
 *
 * Only shown while the microphone is muted, or while something is
 * recording, unless the user asks for it always: an always-visible
 * microphone icon on a machine that never records is noise.
 */
BarItem {
    id: root

    property var hostBar: null

    readonly property bool always: Config.get("bar.microphone.alwaysShow", false)

    visible: Audio.ready && (root.always || Audio.inputMuted)
    tooltip: Audio.inputMuted
        ? qsTr("Microphone muted") : qsTr("Microphone %1%").arg(Audio.inputPercent)

    onActivated: Actions.muteInput()

    content: Icon {
        glyph: Audio.inputMuted ? "\udb81\udf36" : "\udb80\udf6c"
        size: Theme.sizeBody
        color: Audio.inputMuted ? Theme.danger : Theme.textSecondary
    }
}
