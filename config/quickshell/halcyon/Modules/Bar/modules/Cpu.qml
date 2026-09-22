import QtQuick
import qs.Config
import qs.Services
import qs.Components
import "../"

/**
 * Processor utilisation.
 *
 * Shows nothing until there have been two samples: a rate needs a
 * previous reading, and "0%" while we do not yet know is a number that
 * looks true and is not.
 */
BarItem {
    id: root

    property var hostBar: null

    visible: System.hasCpu
    tooltip: {
        const load = System.loadAverage;
        const average = load.length === 3
            ? qsTr(" · load %1 %2 %3").arg(load[0]).arg(load[1]).arg(load[2])
            : "";
        return qsTr("CPU %1%").arg(Math.round(System.cpuPercent))
            + qsTr(" across %n core(s)", "", System.cpuCount) + average;
    }
    onActivated: Actions.run(["shell", "dashboard", "toggle"])

    Component.onCompleted: System.subscribe()
    Component.onDestruction: System.unsubscribe()

    content: Row {
        spacing: Theme.spacingXs

        Icon {
            anchors.verticalCenter: parent.verticalCenter
            glyph: "\udb80\udf3b"
            size: Theme.sizeBody
            color: System.cpuPercent > 85 ? Theme.warning : Theme.textSecondary
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: Math.round(System.cpuPercent) + "%"
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeFootnote
            font.features: ({ "tnum": 1 })
            renderType: Text.QtRendering
        }
    }
}
