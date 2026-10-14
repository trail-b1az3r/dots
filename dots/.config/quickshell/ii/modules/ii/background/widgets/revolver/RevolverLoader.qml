import QtQuick
import qs.modules.common

/**
 * Loads the revolver into a background, in either panel family (ii's Background, waffle's WaffleBackground).
 *
 * The widget is loaded by file path rather than by type, so a fault in it stays inside this Loader and the rest of
 * the background still loads; the reason goes to the shell's log (`halcyon revolver status` shows it). The host
 * passes the screen's size and, in Red Sun, where the painted ring and the car are in its own coordinates.
 */
Loader {
    id: root

    property int screenWidth: 1920
    property int screenHeight: 1080
    /** {x, y, r} of the Red Sun wallpaper's ring, or null. */
    property var sunRing: null
    /** {x, y} of the car on the road in that wallpaper, or null. */
    property var sunCar: null

    function reload(): void {
        if (!Config.options.background.widgets.revolver.enable) {
            source = "";
            return;
        }
        setSource(Qt.resolvedUrl("RevolverWidget.qml"), {
            "screenWidth": root.screenWidth,
            "screenHeight": root.screenHeight,
            "scaledScreenWidth": root.screenWidth,
            "scaledScreenHeight": root.screenHeight,
            "wallpaperScale": 1
        });
    }

    Component.onCompleted: reload()
    onLoaded: {
        item.sunRing = Qt.binding(() => root.sunRing);
        item.sunCar = Qt.binding(() => root.sunCar);
    }
    onStatusChanged: if (status === Loader.Error)
        console.warn("[Halcyon] the revolver did not load; see the errors above (halcyon revolver status)")

    Connections {
        target: Config.options.background.widgets.revolver
        function onEnableChanged(): void {
            root.reload();
        }
    }
}
