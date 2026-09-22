import QtQuick
import qs.Config
import qs.Services
import qs.Components
import "../"

/** Connection state; click opens the network panel. */
BarItem {
    id: root

    property var hostBar: null

    readonly property bool showRate: Config.get("bar.network.showRate", false)

    tooltip: Net.summary
    onActivated: Actions.run(["shell", "control", "network"])

    Component.onCompleted: if (root.showRate) System.subscribe()
    Component.onDestruction: if (root.showRate) System.unsubscribe()

    content: Row {
        spacing: Theme.spacingXs

        Icon {
            anchors.verticalCenter: parent.verticalCenter
            glyph: Net.glyph
            size: Theme.sizeBody
            color: Net.connected ? Theme.text : Theme.textTertiary
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            visible: root.showRate && System.hasNetworkRate
            text: "↓" + System.humanBytes(System.downBytesPerSecond)
                + "  ↑" + System.humanBytes(System.upBytesPerSecond)
            color: Theme.textSecondary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeCaption
            font.features: ({ "tnum": 1 })
            renderType: Text.QtRendering
        }
    }
}
