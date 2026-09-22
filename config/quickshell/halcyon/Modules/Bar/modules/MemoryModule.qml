import QtQuick
import qs.Config
import qs.Services
import qs.Components
import "../"

/** Memory in use, as the kernel's MemAvailable defines "in use". */
BarItem {
    id: root

    property var hostBar: null

    visible: System.memoryTotalKb > 0
    tooltip: {
        const used = System.humanBytes(System.memoryUsedKb * 1024);
        const total = System.humanBytes(System.memoryTotalKb * 1024);
        const swap = System.hasSwap
            ? qsTr(" · swap %1%").arg(Math.round(System.swapPercent)) : "";
        return qsTr("Memory %1 of %2").arg(used).arg(total) + swap;
    }
    onActivated: Actions.run(["shell", "dashboard", "toggle"])

    Component.onCompleted: System.subscribe()
    Component.onDestruction: System.unsubscribe()

    content: Row {
        spacing: Theme.spacingXs

        Icon {
            anchors.verticalCenter: parent.verticalCenter
            glyph: "\udb80\udf5b"
            size: Theme.sizeBody
            color: System.memoryPercent > 90 ? Theme.warning : Theme.textSecondary
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: Math.round(System.memoryPercent) + "%"
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeFootnote
            font.features: ({ "tnum": 1 })
            renderType: Text.QtRendering
        }
    }
}
