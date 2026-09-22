import QtQuick
import qs.Config
import qs.Services
import qs.Components
import "../"

/**
 * Clipboard history.
 *
 * Hidden when history is turned off in privacy settings — a button for
 * a feature the user has disabled is a dead button.
 */
BarItem {
    id: root

    property var hostBar: null

    visible: Config.get("privacy.clipboardHistory", true)
    tooltip: qsTr("Clipboard history")
    onActivated: Actions.run(["shell", "spotlight", "clipboard"])

    content: Icon {
        glyph: "\udb80\udeea"
        size: Theme.sizeBody
        color: Theme.textSecondary
    }
}
