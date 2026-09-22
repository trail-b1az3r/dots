import QtQuick
import qs.Config
import qs.Services
import qs.Components
import "../"

/**
 * The assistant button.
 *
 * Hidden when the assistant is turned off. Pulses while it is
 * listening, so push-to-talk has visible state somewhere other than
 * the overlay.
 */
BarItem {
    id: root

    property var hostBar: null

    visible: Config.get("assistant.enabled", true)
    active: Assistant.busy
    tooltip: Assistant.busy ? qsTr("Assistant is listening") : qsTr("Ask the assistant")

    onActivated: Actions.run(["shell", "assistant", "toggle"])
    onSecondaryActivated: Actions.run(["shell", "assistant", "listen"])

    content: Icon {
        id: glyph

        glyph: "\udb84\udd68"
        size: Theme.sizeBody
        color: Assistant.busy ? Theme.accent : Theme.textSecondary

        SequentialAnimation on opacity {
            running: Assistant.busy && Theme.animationsEnabled
            loops: Animation.Infinite
            alwaysRunToEnd: true

            NumberAnimation { to: 0.45; duration: Theme.durSlow }
            NumberAnimation { to: 1.0; duration: Theme.durSlow }

            onRunningChanged: if (!running) glyph.opacity = 1
        }
    }
}
