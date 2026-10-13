"""Auto-apply at sunset and sunrise: the sun times, the schedule check, and `halcyon-theme auto sun|location`."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HALCYON = Path(__file__).resolve().parent.parent / "dots/.config/hypr/hyprland/halcyon"
sys.path.insert(0, str(HALCYON))

import halcyon_sun as sun  # noqa: E402

_loader = importlib.machinery.SourceFileLoader("halcyon_theme", str(HALCYON / "halcyon-theme"))
_spec = importlib.util.spec_from_loader("halcyon_theme", _loader)
theme = importlib.util.module_from_spec(_spec)
_loader.exec_module(theme)

LONDON = (51.5074, -0.1278)
NEW_YORK = (40.7128, -74.0060)
SYDNEY = (-33.8688, 151.2093)
TROMSO = (69.6496, 18.9560)
BST = timezone(timedelta(hours=1))


def utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


class SunTimesTests(unittest.TestCase):
    def assertNear(self, actual, expected, minutes=3):
        self.assertIsNotNone(actual)
        self.assertLessEqual(abs((actual - expected).total_seconds()), minutes * 60, f"{actual} vs {expected}")

    def test_london_midsummer(self):
        sunrise, sunset = sun.sun_times(date(2026, 6, 21), *LONDON)
        self.assertNear(sunrise, utc(2026, 6, 21, 3, 43))
        self.assertNear(sunset, utc(2026, 6, 21, 20, 21))

    def test_new_york_midwinter(self):
        sunrise, sunset = sun.sun_times(date(2026, 12, 21), *NEW_YORK)
        self.assertNear(sunrise, utc(2026, 12, 21, 12, 16))
        self.assertNear(sunset, utc(2026, 12, 21, 21, 32))

    def test_sydney_sunrise_is_the_previous_utc_day(self):
        sunrise, sunset = sun.sun_times(date(2026, 12, 21), *SYDNEY)
        self.assertNear(sunrise, utc(2026, 12, 20, 18, 41))
        self.assertNear(sunset, utc(2026, 12, 21, 9, 5))

    def test_polar_day_and_night(self):
        self.assertEqual(sun.sun_times(date(2026, 6, 21), *TROMSO), (None, None))
        self.assertEqual(sun.sun_times(date(2026, 12, 21), *TROMSO), (None, None))


class SpecTests(unittest.TestCase):
    NOON = datetime(2026, 6, 21, 12, 0, tzinfo=BST)

    def test_valid_and_invalid_specs(self):
        for good in ("19:30", "00:00", "sunset", "sunrise", "sunset-30", "sunrise+180"):
            self.assertTrue(sun.is_time_spec(good), good)
        for bad in ("25:00", "7:30", "sunset+181", "sundown", "sunset 30", "", None, 1930):
            self.assertFalse(sun.is_time_spec(bad), bad)

    def test_resolve_in_local_time(self):
        self.assertIn(sun.resolve("sunset", self.NOON, LONDON), {"21:19", "21:20", "21:21", "21:22", "21:23"})
        self.assertIn(sun.resolve("sunrise", self.NOON, LONDON), {"04:41", "04:42", "04:43", "04:44", "04:45"})

    def test_offset_moves_the_time(self):
        base = datetime.strptime(sun.resolve("sunset", self.NOON, LONDON), "%H:%M")
        before = datetime.strptime(sun.resolve("sunset-30", self.NOON, LONDON), "%H:%M")
        after = datetime.strptime(sun.resolve("sunset+45", self.NOON, LONDON), "%H:%M")
        self.assertEqual(base - before, timedelta(minutes=30))
        self.assertEqual(after - base, timedelta(minutes=45))

    def test_clock_time_passes_through_and_sun_needs_a_place(self):
        self.assertEqual(sun.resolve("07:15", self.NOON, None), "07:15")
        self.assertIsNone(sun.resolve("sunset", self.NOON, None))
        self.assertIsNone(sun.resolve("sunset", self.NOON, TROMSO))

    def test_offset_past_midnight_does_not_fire_today(self):
        # London midsummer sunset (21:21) plus three hours is after midnight: not today.
        self.assertIsNone(sun.resolve("sunset+180", self.NOON, LONDON))

    def test_parse_location(self):
        self.assertEqual(sun.parse_location("51.5, -0.13"), (51.5, -0.13))
        self.assertEqual(sun.parse_location({"lat": "51.5", "lon": -0.13}), (51.5, -0.13))
        for bad in ("", "51.5", "91,0", "0,181", "a,b", {"lat": 1}, None, "nan,0"):
            self.assertIsNone(sun.parse_location(bad), bad)

    def test_describe(self):
        self.assertEqual(sun.describe("sunset"), "sunset")
        self.assertEqual(sun.describe("sunset-30"), "30 min before sunset")
        self.assertEqual(sun.describe("sunrise+15"), "15 min after sunrise")


class EntryDueTests(unittest.TestCase):
    def at(self, hhmm):
        hour, minute = map(int, hhmm.split(":"))
        return datetime(2026, 6, 21, hour, minute, tzinfo=BST)  # a Sunday

    def test_sunset_entry_fires_at_sunset_only(self):
        when = sun.resolve("sunset", self.at("12:00"), LONDON)
        entry = {"theme": "wallpaper-heaven-kenami", "time": "sunset"}
        self.assertTrue(theme.entry_due(entry, self.at(when), None, LONDON))
        minute_later = (datetime.strptime(when, "%H:%M") + timedelta(minutes=1)).strftime("%H:%M")
        self.assertFalse(theme.entry_due(entry, self.at(minute_later), None, LONDON))

    def test_sunset_entry_without_a_location_never_fires(self):
        when = sun.resolve("sunset", self.at("12:00"), LONDON)
        self.assertFalse(theme.entry_due({"theme": "x", "time": "sunset"}, self.at(when), None, None))

    def test_days_still_narrow_a_sun_time(self):
        when = sun.resolve("sunset", self.at("12:00"), LONDON)
        self.assertFalse(theme.entry_due({"theme": "x", "time": "sunset", "days": [1]}, self.at(when), None, LONDON))
        self.assertTrue(theme.entry_due({"theme": "x", "time": "sunset", "days": [7]}, self.at(when), None, LONDON))

    def test_clock_times_still_work(self):
        self.assertTrue(theme.entry_due({"theme": "x", "time": "19:00"}, self.at("19:00"), None))
        self.assertFalse(theme.entry_due({"theme": "x", "time": "19:00"}, self.at("19:01"), None))
        self.assertFalse(theme.entry_due({"theme": "x", "time": "nonsense"}, self.at("19:00"), None))


class CommandTests(unittest.TestCase):
    def run_tool(self, home, *args):
        env = {k: v for k, v in os.environ.items() if k != "HYPRLAND_INSTANCE_SIGNATURE"}
        env.update(HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"), XDG_STATE_HOME=str(home / ".local/state"))
        return subprocess.run([sys.executable, str(HALCYON / "halcyon-theme"), "auto", *args],
                              capture_output=True, text=True, env=env, check=False)

    def test_location_from_weather_then_settings(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            info = json.loads(self.run_tool(home, "sun").stdout)
            self.assertIsNone(info["location"])
            self.assertIsNone(info["sunset"])

            state = home / ".local/state/halcyon"
            state.mkdir(parents=True)
            (state / "weather.json").write_text(json.dumps({"code": "113", "time": 0, "lat": 51.5, "lon": -0.13}))
            info = json.loads(self.run_tool(home, "sun").stdout)
            self.assertEqual(info["source"], "weather")
            self.assertEqual(info["location"], [51.5, -0.13])

            self.assertEqual(self.run_tool(home, "location", "40.71,-74.0").returncode, 0)
            info = json.loads(self.run_tool(home, "sun").stdout)
            self.assertEqual(info["source"], "settings")
            self.assertIn("40.7100", self.run_tool(home, "location").stdout)

            self.assertNotEqual(self.run_tool(home, "location", "400,0").returncode, 0)
            self.assertEqual(self.run_tool(home, "location", "clear").returncode, 0)
            self.assertEqual(json.loads(self.run_tool(home, "sun").stdout)["source"], "weather")

    def test_list_describes_sun_times(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            cfg = home / ".config/illogical-impulse/config.json"
            cfg.parent.mkdir(parents=True)
            cfg.write_text(json.dumps({"halcyon": {"autoApply": [{"theme": "wallpaper-heaven-kenami", "time": "sunset-30"}]}}))
            out = self.run_tool(home, "list").stdout
            self.assertIn("30 min before sunset (no location yet)", out)


if __name__ == "__main__":
    unittest.main()
