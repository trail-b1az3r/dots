pragma Singleton
import QtQuick
QtObject {
    property QtObject colors: QtObject {
        property color colPrimaryContainer: "#8d2a2a"
        property color colOnLayer1: "#f3e6e4"
        property color colPrimary: "#ff8a7a"
        property color colLayer0: "#0e0b14"
        property color colLayer1: "#16111c"
        property color colOnPrimary: "#5c0e0c"
        property color colLayer0Border: "#3a2c3c"
        property color colShadow: "#80000000"
        property color colTertiary: "#ffb0d6"
    }
    property bool squareBar: false
    property QtObject sizes: QtObject {
        property real baseBarHeight: 40
        property real baseVerticalBarWidth: 46
        property real hyprlandGapsOut: 5
        property real elevationMargin: 10
    }
    property QtObject rounding: QtObject {
        property real small: 12
        property real full: 9999
        property real windowRounding: 18
        property real screenRounding: 23
    }
    property QtObject font: QtObject {
        property QtObject family: QtObject {
            property string main: "sans-serif"
        }
    }
    property QtObject animation: QtObject {
        property QtObject elementMoveFast: QtObject {
            property int duration: 100
        }
    }
}
