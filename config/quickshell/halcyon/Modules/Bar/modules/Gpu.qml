import QtQuick
import Quickshell.Io
import qs.Config
import qs.Services
import qs.Components
import "../"

/**
 * Graphics utilisation.
 *
 * Only some drivers report this. `halcyon status gpu` says whether it
 * could read anything; when it could not, this module hides rather
 * than showing a zero that never moves.
 */
BarItem {
    id: root

    property var hostBar: null

    property var payload: ({})
    readonly property bool hasReading: root.payload.available === true

    visible: root.hasReading
    tooltip: root.payload.tooltip ?? ""
    onActivated: Actions.run(["shell", "dashboard", "toggle"])

    readonly property int interval: Math.max(
        2, Config.get("power.refreshIntervals.acSeconds", 5) * 2) * 1000

    Timer {
        interval: root.interval
        repeat: true
        running: true
        triggeredOnStart: true
        onTriggered: reader.reload()
    }

    Process {
        id: reader

        command: Paths.command(["status", "gpu"])

        function reload(): void {
            reader.running = false;
            reader.running = true;
        }

        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    root.payload = JSON.parse(this.text);
                } catch (error) {
                    root.payload = ({});
                }
            }
        }
    }

    content: Row {
        spacing: Theme.spacingXs

        Icon {
            anchors.verticalCenter: parent.verticalCenter
            glyph: "\udb82\udcae"
            size: Theme.sizeBody
            color: Theme.textSecondary
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: root.payload.text ?? ""
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeFootnote
            font.features: ({ "tnum": 1 })
            renderType: Text.QtRendering
        }
    }
}
