pragma Singleton
pragma ComponentBehavior: Bound

import Quickshell
import Quickshell.Io
import QtQuick
import QtPositioning

import qs.modules.common

Singleton {
    id: root
    // 10 minute
    readonly property int fetchInterval: Config.options.bar.weather.fetchInterval * 60 * 1000
    readonly property string city: Config.options.bar.weather.city
    readonly property bool useUSCS: Config.options.bar.weather.useUSCS
    property bool gpsActive: Config.options.bar.weather.enableGPS

    onUseUSCSChanged: {
        root.getData();
    }
    onCityChanged: {
        root.getData();
    }

    property var location: ({
        valid: false,
        lat: 0,
        lon: 0
    })

    property var data: ({
        uv: 0,
        humidity: 0,
        sunrise: 0,
        sunset: 0,
        windDir: 0,
        wCode: 0,
        city: 0,
        wind: 0,
        precip: 0,
        visib: 0,
        press: 0,
        temp: 0,
        tempFeelsLike: 0,
        lastRefresh: 0,
    })

    function refineData(data) {
        let temp = {};
        temp.uv = data?.current?.uvIndex || 0;
        temp.humidity = (data?.current?.humidity || 0) + "%";
        temp.sunrise = data?.astronomy?.sunrise || "0.0";
        temp.sunset = data?.astronomy?.sunset || "0.0";
        temp.windDir = data?.current?.winddir16Point || "N";
        temp.wCode = data?.current?.weatherCode || "113";
        temp.city = data?.location?.areaName[0]?.value || "City";
        temp.temp = "";
        temp.tempFeelsLike = "";
        if (root.useUSCS) {
            temp.wind = (data?.current?.windspeedMiles || 0) + " mph";
            temp.precip = (data?.current?.precipInches || 0) + " in";
            temp.visib = (data?.current?.visibilityMiles || 0) + " m";
            temp.press = (data?.current?.pressureInches || 0) + " psi";
            temp.temp += (data?.current?.temp_F || 0);
            temp.tempFeelsLike += (data?.current?.FeelsLikeF || 0);
            temp.temp += "°F";
            temp.tempFeelsLike += "°F";
        } else {
            temp.wind = (data?.current?.windspeedKmph || 0) + " km/h";
            temp.precip = (data?.current?.precipMM || 0) + " mm";
            temp.visib = (data?.current?.visibility || 0) + " km";
            temp.press = (data?.current?.pressure || 0) + " hPa";
            temp.temp += (data?.current?.temp_C || 0);
            temp.tempFeelsLike += (data?.current?.FeelsLikeC || 0);
            temp.temp += "°C";
            temp.tempFeelsLike += "°C";
        }
        temp.lastRefresh = DateTime.time + " • " + DateTime.date;
        root.data = temp;
        // Halcyon's auto-apply reads the condition from here, so it needs no fetch of its own,
        // and the place, for themes scheduled at sunset or sunrise (worked out on this computer).
        const halcyonWeather = { code: String(temp.wCode), time: Math.floor(Date.now() / 1000) };
        const lat = parseFloat(data?.location?.latitude);
        const lon = parseFloat(data?.location?.longitude);
        if (!isNaN(lat) && !isNaN(lon)) {
            halcyonWeather.lat = lat;
            halcyonWeather.lon = lon;
        }
        Quickshell.execDetached(["sh", "-c", 'd="${XDG_STATE_HOME:-$HOME/.local/state}/halcyon"; mkdir -p "$d" && printf "%s" "$1" > "$d/weather.json"', "sh", JSON.stringify(halcyonWeather)]);
    }

    function getData() {
        let command = "curl -fsS -m 20 wttr.in";

        if (root.gpsActive && root.location.valid) {
            command += `/${root.location.lat},${root.location.long}`;
        } else {
            command += `/${formatCityName(root.city)}`;
        }

        // format as json; the parts used are picked out below, in QML, so jq isn't needed (without it the
        // widget and the bar were stuck on "--°")
        command += "?format=j1";
        fetcher.command[2] = command;
        fetcher.running = true;
    }

    function formatCityName(cityName) {
        return cityName.trim().split(/\s+/).join('+');
    }

    Component.onCompleted: {
        if (!root.gpsActive) return;
        console.info("[WeatherService] Starting the GPS service.");
        positionSource.start();
    }

    Process {
        id: fetcher
        command: ["bash", "-c", ""]
        stdout: StdioCollector {
            onStreamFinished: {
                if (text.length === 0)
                    return;
                try {
                    const full = JSON.parse(text);
                    // only the current weather, location and astronomy data
                    const parsedData = {
                        current: full?.current_condition?.[0],
                        location: full?.nearest_area?.[0],
                        astronomy: full?.weather?.[0]?.astronomy?.[0]
                    };
                    if (!parsedData.current)
                        throw new Error("wttr.in sent no current weather");
                    root.refineData(parsedData);
                    // console.info(`[ data: ${JSON.stringify(parsedData)}`);
                } catch (e) {
                    console.error(`[WeatherService] ${e.message}`);
                }
            }
        }
    }

    PositionSource {
        id: positionSource
        updateInterval: root.fetchInterval

        onPositionChanged: {
            // update the location if the given location is valid
            // if it fails getting the location, use the last valid location
            if (position.latitudeValid && position.longitudeValid) {
                root.location.lat = position.coordinate.latitude;
                root.location.long = position.coordinate.longitude;
                root.location.valid = true;
                // console.info(`📍 Location: ${position.coordinate.latitude}, ${position.coordinate.longitude}`);
                root.getData();
                // if can't get initialized with valid location deactivate the GPS
            } else {
                root.gpsActive = root.location.valid ? true : false;
                console.error("[WeatherService] Failed to get the GPS location.");
            }
        }

        onValidityChanged: {
            if (!positionSource.valid) {
                positionSource.stop();
                root.location.valid = false;
                root.gpsActive = false;
                Quickshell.execDetached(["notify-send", Translation.tr("Weather Service"), Translation.tr("Cannot find a GPS service. Using the fallback method instead."), "-a", "Shell"]);
                console.error("[WeatherService] Could not aquire a valid backend plugin.");
            }
        }
    }

    // Location services that never answer (geoclue on with no source, or a denied request) left the weather
    // empty for good: after 20 seconds without a place, fetch by city instead (wttr.in finds you by IP without one).
    Timer {
        interval: 20000
        running: root.gpsActive && !root.location.valid
        onTriggered: {
            console.warn("[WeatherService] No location from GPS yet; using the city (or the IP address) instead.");
            root.gpsActive = false;
        }
    }

    Timer {
        running: !root.gpsActive
        repeat: true
        interval: root.fetchInterval
        triggeredOnStart: !root.gpsActive
        onTriggered: root.getData()
    }
}
