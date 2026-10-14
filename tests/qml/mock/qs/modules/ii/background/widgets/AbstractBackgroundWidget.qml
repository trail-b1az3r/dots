import QtQuick
import qs.modules.common

// The parts of the real AbstractBackgroundWidget the revolver uses.
Item {
    property string configEntryName
    property int screenWidth: 1920
    property int screenHeight: 1080
    property int scaledScreenWidth: 1920
    property int scaledScreenHeight: 1080
    property real wallpaperScale: 1
    property bool draggable: false
    property var configEntry: Config.options.background.widgets[configEntryName]
    property real targetX: configEntry ? configEntry.x : 0
    property real targetY: configEntry ? configEntry.y : 0
    x: targetX
    y: targetY
}
