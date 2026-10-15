pragma Singleton
pragma ComponentBehavior: Bound

import qs.modules.common
import QtQuick
import QtPositioning
import Quickshell

/**
 * Where this computer is, for sunrise and sunset (the bar's sun dial and the themes scheduled at sunset): the place
 * set in Settings > Halcyon, else the device's own location (GeoClue, when location is on), else the weather's place
 * (found from the network address when no city is set).
 *
 * The device's position is saved, rounded to about 100 m, in ~/.local/state/halcyon/location.json, where
 * `halcyon-theme auto` reads it. The weather service writes its place to weather.json beside it; the weather runs
 * for this even when no weather card is shown.
 */
Singleton {
    id: root

    readonly property bool setInSettings: (Config.options?.halcyon?.location ?? "") !== ""
    property bool devicePosition: false
    // The weather's place, only needed while there is neither: reading it starts the weather service.
    readonly property var weatherPlace: (!root.setInSettings && !root.devicePosition) ? Weather.data?.city : ""
    readonly property string source: root.setInSettings ? "settings" : root.devicePosition ? "device" : "weather"

    signal updated

    // Called at start-up so the singleton exists from the start: Quickshell makes one only when it is first used.
    function load() {}

    function save(lat, lon) {
        const place = JSON.stringify({ lat: Math.round(lat * 1000) / 1000, lon: Math.round(lon * 1000) / 1000,
            time: Math.floor(Date.now() / 1000) });
        Quickshell.execDetached(["sh", "-c", 'd="${XDG_STATE_HOME:-$HOME/.local/state}/halcyon"; mkdir -p "$d" && printf "%s" "$1" > "$d/location.json"', "sh", place]);
        root.updated();
    }

    PositionSource {
        id: position
        active: !root.setInSettings && valid
        updateInterval: 30 * 60 * 1000
        onPositionChanged: {
            const coordinate = position.position.coordinate;
            if (!position.position.latitudeValid || !position.position.longitudeValid)
                return;
            root.devicePosition = true;
            root.save(coordinate.latitude, coordinate.longitude);
        }
    }

    // The weather's place changes when it is first fetched: the sun dial reads the new one.
    onWeatherPlaceChanged: if (root.weatherPlace)
        Qt.callLater(root.updated)
}
