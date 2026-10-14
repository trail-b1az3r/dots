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
