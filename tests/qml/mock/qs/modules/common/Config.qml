pragma Singleton
import QtQuick

// The few settings the wallpaper widgets read, with the real defaults.
QtObject {
    property QtObject options: QtObject {
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
