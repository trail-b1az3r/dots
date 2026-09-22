import QtQuick
import qs.Config
import qs.Services
import qs.Components
import "../"

/** Charge, and time remaining on hover. Hidden on a desktop. */
BarItem {
    id: root

    property var hostBar: null

    visible: Power.hasBattery
    tooltip: {
        const state = Power.charging ? qsTr("Charging") : qsTr("On battery");
        const remaining = Power.charging ? Power.timeToFull : Power.timeToEmpty;
        if (remaining > 0) {
            const hours = Math.floor(remaining / 3600);
            const minutes = Math.round((remaining % 3600) / 60);
            return qsTr("%1 · %2% · %3h %4m")
                .arg(state).arg(Power.percent).arg(hours).arg(minutes);
        }
        return qsTr("%1 · %2%").arg(state).arg(Power.percent);
    }
    onActivated: Actions.run(["shell", "control", "open"])

    content: Row {
        spacing: Theme.spacingXs

        Icon {
            anchors.verticalCenter: parent.verticalCenter
            glyph: Power.glyph
            size: Theme.sizeBody
            color: {
                if (Power.critical) {
                    return Theme.danger;
                }
                if (Power.low) {
                    return Theme.warning;
                }
                return Power.charging ? Theme.success : Theme.text;
            }
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            visible: Config.get("bar.battery.showPercent", true)
            text: Power.percent + "%"
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sizeFootnote
            font.features: ({ "tnum": 1 })
            renderType: Text.QtRendering
        }
    }
}
