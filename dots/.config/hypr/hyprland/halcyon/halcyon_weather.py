#!/usr/bin/env python3
"""The weather where you are, found from the Wi-Fi around you: `halcyon weather`.

    halcyon weather                     the forecast as last fetched, and where it is for
    halcyon weather update              find where you are and fetch the forecast (a timer does this every 30 minutes)
    halcyon weather location wifi       where you are from the Wi-Fi networks around you (the default), else your IP
    halcyon weather location ip         from your IP address only: nothing about the networks around you is sent
    halcyon weather location "Oslo"     always that place (looked up once by name), or "LAT, LON"
    halcyon weather units metric|imperial
    halcyon weather on|off|auto         fetch the weather always, never, or while Summit is the desktop shell (auto,
                                        the default: Summit's bar is what shows it)
    halcyon weather --json

How it finds you: NetworkManager lists the Wi-Fi access points it can hear (nmcli; no connection needed), and their
hardware addresses and signal strengths go to BeaconDB (beacondb.net), a community-run location service that replaces
Mozilla's, which answers with a latitude and longitude, usually to within a few hundred metres. Networks whose name
ends in "_nomap" (their owners' opt-out) and phones' hotspots (locally administered addresses) are never sent. With
fewer than two networks in range, or when BeaconDB does not know them, your IP address gives the town instead
(ipapi.co). The place's name comes from OpenStreetMap (Nominatim), and the forecast from Open-Meteo: none of them needs
an account or a key.

The forecast is written to ~/.cache/halcyon/weather.json, which Summit's bar and its forecast window read; the
settings are in ~/.config/halcyon/weather.json.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
CONFIG = Path(os.environ.get("XDG_CONFIG_HOME") or HOME / ".config") / "halcyon/weather.json"
CACHE = Path(os.environ.get("XDG_CACHE_HOME") or HOME / ".cache") / "halcyon/weather.json"

USER_AGENT = "Halcyon-weather/1.0 (+https://github.com/trail-b1az3r/dots)"
BEACONDB = "https://api.beacondb.net/v1/geolocate"
IPAPI = "https://ipapi.co/json/"
NOMINATIM_REVERSE = "https://nominatim.openstreetmap.org/reverse"
OPEN_METEO_GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = 15
# A place name is looked up again only after moving this far (Nominatim asks for few requests).
RENAME_KM = 3.0
DEFAULTS = {"enabled": "auto", "location": "wifi", "units": "metric"}
DESKTOP_SHELL = Path(os.environ.get("XDG_STATE_HOME") or HOME / ".local/state") / "halcyon/desktop-shell"

# WMO weather interpretation codes (what Open-Meteo returns) in words.
WORDS = {
    0: "Clear", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Fog", 48: "Icy fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle", 56: "Freezing drizzle", 57: "Freezing drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain", 66: "Freezing rain", 67: "Freezing rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Showers", 81: "Showers", 82: "Heavy showers", 85: "Snow showers", 86: "Snow showers",
    95: "Thunderstorm", 96: "Thunderstorm, hail", 99: "Thunderstorm, hail",
}
# The same codes as freedesktop icon names (rofi's list shows them).
ICONS = (
    ((0, 1), "weather-clear"), ((2,), "weather-few-clouds"), ((3,), "weather-overcast"), ((45, 48), "weather-fog"),
    ((51, 53, 55, 56, 57, 61, 80), "weather-showers-scattered"), ((63, 65, 66, 67, 81, 82), "weather-showers"),
    ((71, 73, 75, 77, 85, 86), "weather-snow"), ((95, 96, 99), "weather-storm"),
)


def words(code) -> str:
    return WORDS.get(int(code), "—") if isinstance(code, (int, float)) else "—"


def icon(code) -> str:
    for codes, name in ICONS:
        if isinstance(code, (int, float)) and int(code) in codes:
            return name
    return "weather-few-clouds"


# Settings ------------------------------------------------------------------------------------------------------------

def load_settings(path: Path = CONFIG) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    settings = dict(DEFAULTS)
    if isinstance(data, dict):
        settings.update({k: v for k, v in data.items() if k in DEFAULTS or k == "place"})
    if settings["units"] not in ("metric", "imperial"):
        settings["units"] = "metric"
    if settings["enabled"] not in (True, False, "auto"):
        settings["enabled"] = "auto"
    return settings


def summit_runs(path: Path | None = None) -> bool:
    try:
        return (path or DESKTOP_SHELL).read_text(encoding="utf-8").strip() == "Summit"
    except OSError:
        return False


def wanted(settings: dict) -> bool:
    """Whether to fetch the weather: on, or auto while Summit is the desktop shell."""
    enabled = settings.get("enabled", "auto")
    return summit_runs() if enabled == "auto" else bool(enabled)


def save_settings(settings: dict, path: Path = CONFIG) -> None:
    write_atomic(path, json.dumps(settings, indent=2) + "\n")


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


# HTTP ----------------------------------------------------------------------------------------------------------------

def fetch_json(url: str, params: dict | None = None, body: dict | None = None, opener=urllib.request.urlopen):
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url, data=data, headers={
        "User-Agent": USER_AGENT, "Accept": "application/json",
        **({"Content-Type": "application/json"} if data is not None else {}),
    })
    with opener(request, timeout=TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


# Where you are -------------------------------------------------------------------------------------------------------

def _unescape_nmcli(field: str) -> str:
    return field.replace("\\:", ":").replace("\\\\", "\\")


def _split_nmcli(line: str) -> list[str]:
    """nmcli -t fields: ':' separated, with ':' inside a field written '\\:'."""
    return [_unescape_nmcli(part) for part in re.split(r"(?<!\\):", line)]


def locally_administered(mac: str) -> bool:
    try:
        return bool(int(mac.split(":")[0], 16) & 0x02)
    except ValueError:
        return True


def wifi_access_points(run=subprocess.run) -> list[dict]:
    """The access points in range, as BeaconDB wants them: no opted-out networks, no phone hotspots."""
    seen: dict[str, dict] = {}
    if shutil.which("nmcli"):
        try:
            out = run(["nmcli", "-t", "-f", "BSSID,SIGNAL,SSID", "device", "wifi", "list", "--rescan", "auto"],
                      capture_output=True, text=True, timeout=30, check=False)
        except (OSError, subprocess.SubprocessError):
            out = None
        for line in (out.stdout.splitlines() if out is not None and out.returncode == 0 else []):
            fields = _split_nmcli(line)
            if len(fields) < 3:
                continue
            bssid, signal, ssid = fields[0].lower(), fields[1], ":".join(fields[2:])
            if not re.fullmatch(r"([0-9a-f]{2}:){5}[0-9a-f]{2}", bssid):
                continue
            if ssid.endswith("_nomap") or locally_administered(bssid):
                continue
            try:
                quality = max(0, min(100, int(signal)))
            except ValueError:
                continue
            # NetworkManager gives a 0..100 quality; BeaconDB wants dBm. Roughly: 100 is -50 dBm, 0 is -100 dBm.
            dbm = round(quality / 2 - 100)
            if bssid not in seen or seen[bssid]["signalStrength"] < dbm:
                seen[bssid] = {"macAddress": bssid, "signalStrength": dbm}
    return sorted(seen.values(), key=lambda ap: -ap["signalStrength"])[:40]


def locate_wifi(points: list[dict], fetch=fetch_json) -> dict | None:
    if len(points) < 2:
        return None
    try:
        answer = fetch(BEACONDB, body={"considerIp": False, "wifiAccessPoints": points})
    except Exception:  # noqa: BLE001  (any network or service failure: try the next way)
        return None
    loc = (answer or {}).get("location") or {}
    if not isinstance(loc.get("lat"), (int, float)) or not isinstance(loc.get("lng"), (int, float)):
        return None
    return {"lat": float(loc["lat"]), "lon": float(loc["lng"]), "accuracy": answer.get("accuracy"),
            "source": "wifi", "networks": len(points)}


def locate_ip(fetch=fetch_json) -> dict | None:
    """The town your IP address is in: ipapi.co, else BeaconDB's own IP lookup."""
    try:
        answer = fetch(IPAPI)
        lat, lon = answer.get("latitude"), answer.get("longitude")
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
            return {"lat": float(lat), "lon": float(lon), "source": "ip", "name": answer.get("city") or ""}
    except Exception:  # noqa: BLE001
        pass
    try:
        answer = fetch(BEACONDB, body={"considerIp": True})
    except Exception:  # noqa: BLE001
        return None
    loc = (answer or {}).get("location") or {}
    if not isinstance(loc.get("lat"), (int, float)) or not isinstance(loc.get("lng"), (int, float)):
        return None
    return {"lat": float(loc["lat"]), "lon": float(loc["lng"]), "accuracy": answer.get("accuracy"), "source": "ip"}


def geocode(name: str, fetch=fetch_json) -> dict | None:
    """A place you named, as a latitude and longitude ("LAT, LON" is taken as it is)."""
    match = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*", name)
    if match:
        lat, lon = float(match.group(1)), float(match.group(2))
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return {"lat": lat, "lon": lon, "source": "fixed", "name": ""}
        return None
    try:
        answer = fetch(OPEN_METEO_GEOCODE, {"name": name, "count": 1, "format": "json"})
    except Exception:  # noqa: BLE001
        return None
    results = (answer or {}).get("results") or []
    if not results:
        return None
    first = results[0]
    label = ", ".join(part for part in (first.get("name"), first.get("country")) if part)
    return {"lat": float(first["latitude"]), "lon": float(first["longitude"]), "source": "fixed", "name": label}


def distance_km(a: dict, b: dict) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (a["lat"], a["lon"], b["lat"], b["lon"]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(min(1.0, h)))


def place_name(where: dict, previous: dict | None, fetch=fetch_json) -> str:
    """The town's name: kept from the last fetch while you are near the same place, else asked of OpenStreetMap."""
    if where.get("name"):
        return where["name"]
    if previous and previous.get("name") and isinstance(previous.get("lat"), (int, float)) \
            and distance_km(where, previous) < RENAME_KM:
        return previous["name"]
    try:
        answer = fetch(NOMINATIM_REVERSE, {"format": "jsonv2", "lat": f"{where['lat']:.4f}",
                                           "lon": f"{where['lon']:.4f}", "zoom": 10})
    except Exception:  # noqa: BLE001
        return ""
    address = (answer or {}).get("address") or {}
    for key in ("city", "town", "village", "municipality", "suburb", "county", "state"):
        if address.get(key):
            return address[key]
    return (answer or {}).get("name") or ""


def locate(settings: dict, previous: dict | None, run=subprocess.run, fetch=fetch_json) -> dict | None:
    mode = settings.get("location", "wifi")
    if mode not in ("wifi", "ip"):
        fixed = settings.get("place")
        if isinstance(fixed, dict) and isinstance(fixed.get("lat"), (int, float)):
            return dict(fixed, source="fixed")
        found = geocode(str(mode), fetch)
        if found:
            settings["place"] = found
            save_settings(settings)
        return found
    where = None
    if mode == "wifi":
        where = locate_wifi(wifi_access_points(run), fetch)
    return where or locate_ip(fetch)


# The forecast --------------------------------------------------------------------------------------------------------

def forecast(where: dict, units: str, fetch=fetch_json) -> dict:
    params = {
        "latitude": f"{where['lat']:.4f}", "longitude": f"{where['lon']:.4f}", "timezone": "auto", "forecast_days": 7,
        "current": "temperature_2m,apparent_temperature,weather_code,is_day,wind_speed_10m,relative_humidity_2m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset",
        "hourly": "temperature_2m,weather_code,precipitation_probability",
    }
    if units == "imperial":
        params.update({"temperature_unit": "fahrenheit", "wind_speed_unit": "mph"})
    return fetch(OPEN_METEO, params)


def shape(raw: dict, where: dict, name: str, units: str, now: datetime | None = None) -> dict:
    """Open-Meteo's answer in the shape Summit reads (services/Weather.qml)."""
    current = raw.get("current") or {}
    daily = raw.get("daily") or {}
    hourly = raw.get("hourly") or {}
    days = []
    for i, day in enumerate(daily.get("time") or []):
        def at(key, i=i):
            values = daily.get(key) or []
            return values[i] if i < len(values) else None
        days.append({"date": day, "max": at("temperature_2m_max"), "min": at("temperature_2m_min"),
                     "weather_code": at("weather_code"), "rain": at("precipitation_probability_max"),
                     "sunrise": at("sunrise"), "sunset": at("sunset")})
    hours = []
    start = (current.get("time") or "")[:13]
    times = hourly.get("time") or []
    first = next((i for i, t in enumerate(times) if t[:13] >= start), 0) if start else 0
    for i in range(first, min(first + 24, len(times))):
        def at(key, i=i):
            values = hourly.get(key) or []
            return values[i] if i < len(values) else None
        hours.append({"time": times[i], "temperature": at("temperature_2m"), "weather_code": at("weather_code"),
                      "rain": at("precipitation_probability")})
    return {
        "updated": (now or datetime.now(timezone.utc)).isoformat(timespec="seconds"),
        "place": {"name": name, "source": where.get("source", ""), "lat": round(where["lat"], 4),
                  "lon": round(where["lon"], 4), "accuracy": where.get("accuracy")},
        "units": {"temperature": "°F" if units == "imperial" else "°C", "wind": "mph" if units == "imperial" else "km/h"},
        "current": {"temperature": current.get("temperature_2m"), "feels_like": current.get("apparent_temperature"),
                    "weather_code": current.get("weather_code"), "is_day": current.get("is_day", 1),
                    "wind_speed": current.get("wind_speed_10m"), "humidity": current.get("relative_humidity_2m")},
        "daily": days,
        "hourly": hours,
    }


def read_cache(path: Path = CACHE) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def update(settings: dict | None = None, run=subprocess.run, fetch=fetch_json, cache: Path = CACHE) -> dict:
    settings = settings or load_settings()
    if settings.get("enabled") is False:
        raise RuntimeError("the weather is off (halcyon weather on)")
    previous = read_cache(cache)
    where = locate(settings, (previous or {}).get("place"), run, fetch)
    if not where:
        raise RuntimeError("couldn't tell where you are: no Wi-Fi networks BeaconDB knows, and no answer for your IP")
    name = place_name(where, (previous or {}).get("place"), fetch)
    data = shape(forecast(where, settings["units"], fetch), where, name, settings["units"])
    write_atomic(cache, json.dumps(data, indent=1) + "\n")
    return data


# Output --------------------------------------------------------------------------------------------------------------

def temperature(value, unit) -> str:
    return f"{round(value)}{unit}" if isinstance(value, (int, float)) else "—"


def day_label(date: str, index: int) -> str:
    if index == 0:
        return "Today"
    try:
        return datetime.strptime(date, "%Y-%m-%d").strftime("%a %-d")
    except ValueError:
        return date


def rows(data: dict) -> list[tuple[str, str]]:
    """The forecast as (text, icon) rows: now, then a row a day."""
    unit = (data.get("units") or {}).get("temperature", "°")
    current = data.get("current") or {}
    out = [(f"Now   {temperature(current.get('temperature'), unit)}  {words(current.get('weather_code'))}"
            f"   ·   feels {temperature(current.get('feels_like'), unit)}", icon(current.get("weather_code")))]
    for i, day in enumerate(data.get("daily") or []):
        rain = f"   ·   {day['rain']}% rain" if isinstance(day.get("rain"), (int, float)) and day["rain"] >= 20 else ""
        out.append((f"{day_label(day.get('date', ''), i):<8}  {temperature(day.get('max'), unit)} / "
                    f"{temperature(day.get('min'), unit)}   {words(day.get('weather_code'))}{rain}",
                    icon(day.get("weather_code"))))
    return out


def describe_source(place: dict) -> str:
    source = place.get("source")
    if source == "wifi":
        accuracy = place.get("accuracy")
        return f"from nearby Wi-Fi (±{round(accuracy)} m)" if isinstance(accuracy, (int, float)) else "from nearby Wi-Fi"
    return {"ip": "from your IP address", "fixed": "the place you set"}.get(source, "")


def print_status(data: dict | None, settings: dict) -> None:
    enabled = settings.get("enabled", "auto")
    state = {True: "on", False: "off"}.get(enabled, f"auto ({'on: Summit runs' if summit_runs() else 'off: Summit is not the shell'})")
    print(f"weather      {state}")
    print(f"location     {settings['location']}   units {settings['units']}")
    if not data:
        print("forecast     none yet (halcyon weather update)")
        return
    place = data.get("place") or {}
    print(f"place        {place.get('name') or 'unknown'}, {describe_source(place)}")
    print(f"updated      {data.get('updated', '?')}")
    for text, _icon in rows(data):
        print(f"  {text}")


def login(run=subprocess.run) -> None:
    """At login, and when the desktop shell changes: the timer that keeps the forecast fresh runs while the weather is
    wanted, and is stopped while it is not."""
    if not shutil.which("systemctl"):
        return
    action = ["enable", "--now"] if wanted(load_settings()) else ["disable", "--now"]
    run(["systemctl", "--user", *action, "halcyon-weather.timer"],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="halcyon weather", description=__doc__.split("\n")[0])
    parser.add_argument("command", nargs="?", default="status",
                        choices=["status", "update", "location", "units", "on", "off", "auto", "rows", "place",
                                 "login"])
    parser.add_argument("value", nargs="?")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    settings = load_settings()

    if args.command == "update":
        try:
            data = update(settings)
        except Exception as error:  # noqa: BLE001
            print(f"halcyon weather: {error}", file=sys.stderr)
            return 1
        print(json.dumps(data) if args.json else
              f"{(data['place'] or {}).get('name') or 'here'}: {rows(data)[0][0]}")
        return 0
    if args.command == "location":
        if not args.value:
            print(settings["location"])
            return 0
        settings["location"] = args.value if args.value in ("wifi", "ip") else args.value.strip()
        settings.pop("place", None)
        save_settings(settings)
        print(f"location: {settings['location']}")
        return 0
    if args.command == "units":
        if args.value not in ("metric", "imperial"):
            print("units: metric or imperial", file=sys.stderr)
            return 2
        settings["units"] = args.value
        save_settings(settings)
        return 0
    if args.command in ("on", "off", "auto"):
        settings["enabled"] = {"on": True, "off": False}.get(args.command, "auto")
        save_settings(settings)
        login()
        print(f"weather {args.command}")
        return 0
    if args.command == "login":
        login()
        return 0

    data = read_cache()
    if args.command == "rows":
        if not data:
            return 1
        for text, name in rows(data):
            sys.stdout.write(f"{text}\0icon\x1f{name}\n")
        return 0
    if args.command == "place":
        place = (data or {}).get("place") or {}
        if not place:
            return 1
        print(" · ".join(part for part in (place.get("name"), describe_source(place)) if part))
        return 0
    if args.json:
        print(json.dumps({"settings": settings, "forecast": data}))
    else:
        print_status(data, settings)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
