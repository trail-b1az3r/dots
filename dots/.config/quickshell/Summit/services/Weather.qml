pragma Singleton
pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Io

/**
 * The weather, as halcyon-weather last fetched it (~/.cache/halcyon/weather.json): the place found from nearby Wi-Fi
 * networks (or the network address, or the place set with `halcyon weather location`), now and the next days.
 * halcyon-weather.timer refreshes it; `refresh()` asks for it now.
 */
Singleton {
    id: root

    readonly property string cacheFile: (Quickshell.env("XDG_CACHE_HOME") || (Quickshell.env("HOME") + "/.cache")) + "/halcyon/weather.json"
    property var data: null
    readonly property bool ready: data !== null && data.current !== undefined
    readonly property string place: data?.place?.name ?? ""
    readonly property real temperature: data?.current?.temperature ?? 0
    readonly property string unit: data?.units?.temperature ?? "°C"
    readonly property int code: data?.current?.weather_code ?? -1
    readonly property bool isDay: (data?.current?.is_day ?? 1) === 1
    readonly property var days: data?.daily ?? []
    readonly property string source: data?.place?.source ?? ""

    function refresh() {
        Quickshell.execDetached(["systemctl", "--user", "start", "halcyon-weather.service"]);
    }

    // WMO weather codes (Open-Meteo) to Material Symbols and words.
    function icon(code, day) {
        if (code === 0) return day ? "clear_day" : "bedtime";
        if (code <= 2) return day ? "partly_cloudy_day" : "partly_cloudy_night";
        if (code === 3) return "cloud";
        if (code === 45 || code === 48) return "foggy";
        if (code >= 51 && code <= 67) return "rainy";
        if (code >= 71 && code <= 77) return "weather_snowy";
        if (code >= 80 && code <= 82) return "rainy";
        if (code >= 85 && code <= 86) return "weather_snowy";
        if (code >= 95) return "thunderstorm";
        return "cloud";
    }
    function words(code) {
        const w = { 0: "Clear", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Fog", 48: "Fog",
            51: "Drizzle", 53: "Drizzle", 55: "Drizzle", 61: "Rain", 63: "Rain", 65: "Heavy rain",
            71: "Snow", 73: "Snow", 75: "Heavy snow", 80: "Showers", 81: "Showers", 82: "Heavy showers",
            95: "Thunderstorm", 96: "Thunderstorm", 99: "Thunderstorm" };
        return w[code] ?? "";
    }

    FileView {
        path: root.cacheFile
        watchChanges: true
        onFileChanged: reload()
        onLoaded: {
            try {
                root.data = JSON.parse(text());
            } catch (e) {
                root.data = null;
            }
        }
        onLoadFailed: root.data = null
    }
}
