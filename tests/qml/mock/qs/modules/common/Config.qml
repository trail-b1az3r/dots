pragma Singleton
import QtQuick

// The few settings the wallpaper widgets and the bar's groups read, with the real defaults.
QtObject {
    property QtObject options: QtObject {
        property QtObject bar: QtObject {
            property int cornerStyle: 0
            property bool floatStyleShadow: true
            property bool borderless: false
            property bool showBackground: true
            property bool vertical: false
        }
        property QtObject halcyon: QtObject {
            property string theme: ""
            property bool glassTheme: false
        }
        property QtObject background: QtObject {
            property QtObject widgets: QtObject {
                property QtObject revolver: QtObject {
                    property bool enable: true
                    property string placementStrategy: "free"
                    property real x: 200
                    property real y: 150
                    property string source: "steam"
                    property string mode: "recent"
                    property int size: 300
                    property bool followRing: true
                }
            }
        }
    }
}
