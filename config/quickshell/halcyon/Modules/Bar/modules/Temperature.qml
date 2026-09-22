import QtQuick
import qs.Config
import qs.Services
import qs.Components
import "../"

/**
 * CPU temperature.
 *
 * Hidden entirely when no sensor is present. A virtual machine or a
 * board with no hwmon CPU driver has no temperature, and showing a
 * dash where a number belongs invites the question "is it broken?"
 * every time someone looks at the bar.
 */
BarItem {
    id: root

    property var hostBar: null

    readonly property int warnAbove: Config.get("bar.temperature.warnAbove", 80)

    visible: System.hasTemperature
    tooltip: qsTr("CPU temperature %1 °C").arg(Math.round(System.temperature))
    onActivated: Actions.run(["shell", "dashboard", "toggle"])

    Component.onCompleted: System.subscribe()
    Component.onDestruction: System.unsubscribe()

    content: Row {
        spacing: Theme.spacingXs

        Icon {
            anchors.verticalCenter: parent.verticalCenter
            glyph: "\udb85\udd0f"
            size: Theme.sizeBody
            color: System.temperature >= root.warnAbove
                ? Theme.danger : Theme.textSecondary
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: Math.round(System.temperature) + "°"
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeFootnote
            font.features: ({ "tnum": 1 })
            renderType: Text.QtRendering
        }
    }
}
