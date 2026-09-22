import QtQuick
import qs.Config
import qs.Services
import qs.Components
import "../"

/** The active power profile; click to cycle. */
BarItem {
    id: root

    property var hostBar: null

    readonly property string profile: Config.get("power.profile", "balanced")

    tooltip: {
        if (root.profile === "performance") {
            return qsTr("Performance · click to cycle");
        }
        if (root.profile === "battery-saver") {
            return qsTr("Battery saver · click to cycle");
        }
        return qsTr("Balanced · click to cycle");
    }

    onActivated: Actions.run(["power", "cycle"])

    content: Icon {
        glyph: {
            if (root.profile === "performance") {
                return "\udb81\udd0f";
            }
            if (root.profile === "battery-saver") {
                return "\udb80\udc84";
            }
            return "\udb81\udf6f";
        }
        size: Theme.sizeBody
        color: {
            if (root.profile === "performance") {
                return Theme.warning;
            }
            if (root.profile === "battery-saver") {
                return Theme.success;
            }
            return Theme.textSecondary;
        }
    }
}
