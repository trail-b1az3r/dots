import QtQuick
import qs.Config
import qs.Services
import qs.Components
import "../"

/** Bluetooth state. Hidden when the machine has no adapter. */
BarItem {
    id: root

    property var hostBar: null

    visible: Bt.available
    tooltip: Bt.summary
    onActivated: Actions.run(["shell", "control", "bluetooth"])
    onSecondaryActivated: Bt.toggle()

    content: Icon {
        glyph: Bt.glyph
        size: Theme.sizeBody
        color: {
            if (!Bt.enabled) {
                return Theme.textTertiary;
            }
            return Bt.connectedDevices.length > 0 ? Theme.accent : Theme.text;
        }
    }
}
