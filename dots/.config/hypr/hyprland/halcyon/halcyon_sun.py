"""Sunrise and sunset for auto-apply, worked out on this computer from a latitude and longitude.

An auto-apply time is either a clock time ("19:30") or the sun: "sunset", "sunrise", or either with an offset in
minutes ("sunset-30" is half an hour before sunset). The sun times use NOAA's solar equations, which are within a
minute or two of the published times; that is what auto-apply's one-minute timer can tell apart anyway.

Where the sun does not set or rise that day (midnight sun, polar night), a sun time never fires.
"""

from __future__ import annotations

import math
import re
from datetime import date, datetime, timedelta, timezone

SUN_TIME = re.compile(r"^(sunrise|sunset)(?:([+-])([0-9]{1,3}))?$")
CLOCK_TIME = re.compile(r"^([01][0-9]|2[0-3]):[0-5][0-9]$")
MAX_OFFSET = 180  # minutes
ZENITH = 90.833  # the sun's centre at the horizon, with refraction and the disc's radius


def parse_location(value: object) -> tuple[float, float] | None:
    """(latitude, longitude) from "lat, lon" or a {"lat", "lon"} object. None if missing or out of range."""
    if isinstance(value, dict):
        lat, lon = value.get("lat"), value.get("lon")
    elif isinstance(value, str) and value.count(",") == 1:
        lat, lon = (part.strip() for part in value.split(","))
    else:
        return None
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180) or math.isnan(lat) or math.isnan(lon):
        return None
    return lat, lon


def sun_times(day: date, lat: float, lon: float) -> tuple[datetime | None, datetime | None]:
    """Sunrise and sunset on that day at that place, in UTC. None for one that does not happen that day."""
    gamma = 2 * math.pi / 365 * (day.timetuple().tm_yday - 1)  # fractional year, at noon
    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(gamma) - 0.032077 * math.sin(gamma)
                       - 0.014615 * math.cos(2 * gamma) - 0.040849 * math.sin(2 * gamma))
    decl = (0.006918 - 0.399912 * math.cos(gamma) + 0.070257 * math.sin(gamma)
            - 0.006758 * math.cos(2 * gamma) + 0.000907 * math.sin(2 * gamma)
            - 0.002697 * math.cos(3 * gamma) + 0.00148 * math.sin(3 * gamma))
    phi = math.radians(lat)
    cos_ha = math.cos(math.radians(ZENITH)) / (math.cos(phi) * math.cos(decl)) - math.tan(phi) * math.tan(decl)
    if not -1 <= cos_ha <= 1:
        return None, None  # polar night (> 1) or midnight sun (< -1)
    ha = math.degrees(math.acos(cos_ha))
    midnight = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    sunrise = midnight + timedelta(minutes=720 - 4 * (lon + ha) - eqtime)
    sunset = midnight + timedelta(minutes=720 - 4 * (lon - ha) - eqtime)
    return sunrise, sunset


def is_time_spec(value: object) -> bool:
    """Whether a saved auto-apply time is valid: a clock time, or the sun with an offset of up to MAX_OFFSET."""
    if not isinstance(value, str):
        return False
    if CLOCK_TIME.match(value):
        return True
    match = SUN_TIME.match(value)
    return bool(match) and (match.group(3) is None or int(match.group(3)) <= MAX_OFFSET)


def resolve(spec: str, now: datetime, location: tuple[float, float] | None) -> str | None:
    """The "HH:MM" a time spec means today, in now's time zone. None when it cannot fire today.

    `now` must be timezone-aware for sun times; a clock time is returned as it is.
    """
    if CLOCK_TIME.match(spec):
        return spec
    match = SUN_TIME.match(spec)
    if not match or location is None:
        return None
    event, sign, amount = match.groups()
    offset = int(amount or 0) * (-1 if sign == "-" else 1)
    if abs(offset) > MAX_OFFSET:
        return None
    sunrise, sunset = sun_times(now.date(), *location)
    moment = sunrise if event == "sunrise" else sunset
    if moment is None:
        return None
    local = (moment + timedelta(minutes=offset)).astimezone(now.tzinfo)
    # Rounded to the minute, the way a clock shows it. A shifted time that falls on another day does not fire today.
    local = (local + timedelta(seconds=30)).replace(second=0, microsecond=0)
    if local.date() != now.date():
        return None
    return local.strftime("%H:%M")


def describe(spec: str) -> str:
    """A spec in words: "sunset", "30 min before sunset"."""
    match = SUN_TIME.match(spec)
    if not match:
        return spec
    event, sign, amount = match.groups()
    if not amount or int(amount) == 0:
        return event
    return f"{int(amount)} min {'before' if sign == '-' else 'after'} {event}"


def day_progress(now: datetime, location: tuple[float, float] | None) -> float | None:
    """Where the sun is between sunrise (0) and sunset (1) right now; below 0 before dawn, above 1 after dusk.
    None without a location, or on a day with no sunrise or sunset."""
    if location is None:
        return None
    sunrise, sunset = sun_times(now.date(), *location)
    if sunrise is None or sunset is None:
        return None
    span = (sunset - sunrise).total_seconds()
    if span <= 0:
        return None
    return (now - sunrise).total_seconds() / span


def next_due(entries: list[dict], now: datetime, location: tuple[float, float] | None,
             names: dict[str, str] | None = None) -> dict | None:
    """The next auto-apply schedule to fire after `now` (within two days): {theme, name, at, minutes, spec, weather}.

    Weather-only schedules cannot be foreseen and are left out; a schedule that also needs some weather is
    returned with that weather, since it fires only if the weather matches then.
    """
    best = None
    for entry in entries:
        spec = entry.get("time")
        if not isinstance(spec, str) or not is_time_spec(spec):
            continue
        days = entry.get("days") or []
        for offset in range(0, 3):
            day = now + timedelta(days=offset)
            if days and day.isoweekday() not in days:
                continue
            hhmm = resolve(spec, day, location)
            if hhmm is None:
                continue
            hour, minute = (int(part) for part in hhmm.split(":"))
            when = day.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if when <= now:
                continue
            if best is None or when < best[0]:
                best = (when, entry, spec)
            break
    if best is None:
        return None
    when, entry, spec = best
    theme = entry["theme"]
    return {"theme": theme, "name": (names or {}).get(theme, theme), "at": when.strftime("%H:%M"),
            "day": {0: "today", 1: "tomorrow"}.get((when.date() - now.date()).days, when.strftime("%a")),
            "minutes": int((when - now).total_seconds() // 60), "spec": spec, "when": describe(spec),
            "weather": entry.get("weather") or ""}
