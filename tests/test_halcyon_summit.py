"""Summit (the HyperNeo v2 theme's shell), its Wi-Fi weather, and MacShell's theme picker.
Run: python3 -m unittest discover -s tests"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HALCYON = ROOT / "dots/.config/hypr/hyprland/halcyon"
UNITS = ROOT / "dots/.config/systemd/user"
SUMMIT = ROOT / "dots/.config/quickshell/Summit"
MACSHELL = ROOT / "dots/.config/quickshell/MacShell"
sys.path.insert(0, str(HALCYON))

import halcyon_weather as weather  # noqa: E402

_loader = importlib.machinery.SourceFileLoader("halcyon_theme_summit", str(HALCYON / "halcyon-theme"))
_spec = importlib.util.spec_from_loader("halcyon_theme_summit", _loader)
theme = importlib.util.module_from_spec(_spec)
_loader.exec_module(theme)

NMCLI = """\
A8\\:BB\\:CC\\:00\\:11\\:22:80:Home
A8\\:BB\\:CC\\:00\\:11\\:22:60:Home
0C\\:BB\\:CC\\:00\\:11\\:33:40:Cafe\\:Guest
10\\:BB\\:CC\\:00\\:11\\:44:70:Neighbour_nomap
12\\:BB\\:CC\\:00\\:11\\:55:90:My phone
"""


def nmcli_run(cmd, **_kw):
    return subprocess.CompletedProcess(cmd, 0, stdout=NMCLI, stderr="")


class WifiTests(unittest.TestCase):
    def test_access_points_leave_out_opted_out_networks_and_phones(self):
        with unittest.mock.patch.object(weather.shutil, "which", return_value="/usr/bin/nmcli"):
            points = weather.wifi_access_points(nmcli_run)
        macs = [p["macAddress"] for p in points]
        # strongest reading of each, the ":" inside a name doesn't split it, no _nomap, no locally administered MAC
        self.assertEqual(macs, ["a8:bb:cc:00:11:22", "0c:bb:cc:00:11:33"])
        self.assertEqual(points[0]["signalStrength"], -60)   # 80% -> -60 dBm

    def test_wifi_needs_two_networks(self):
        calls = []
        self.assertIsNone(weather.locate_wifi([{"macAddress": "a8:bb:cc:00:11:22", "signalStrength": -60}],
                                              lambda *a, **k: calls.append(a)))
        self.assertEqual(calls, [])

    def test_beacondb_answer(self):
        sent = {}

        def fetch(url, params=None, body=None):
            sent.update(url=url, body=body)
            return {"location": {"lat": 43.48, "lng": -110.76}, "accuracy": 80}

        points = [{"macAddress": "a8:bb:cc:00:11:22", "signalStrength": -60},
                  {"macAddress": "0c:bb:cc:00:11:33", "signalStrength": -80}]
        where = weather.locate_wifi(points, fetch)
        self.assertEqual(where["source"], "wifi")
        self.assertEqual((where["lat"], where["lon"]), (43.48, -110.76))
        self.assertEqual(sent["url"], weather.BEACONDB)
        self.assertFalse(sent["body"]["considerIp"])       # the Wi-Fi answer is not mixed with the IP's

    def test_ip_fallback(self):
        def fetch(url, params=None, body=None):
            if url == weather.BEACONDB:
                return {"location": {}}
            return {"latitude": 59.9, "longitude": 10.7, "city": "Oslo"}

        settings = dict(weather.DEFAULTS)
        with unittest.mock.patch.object(weather.shutil, "which", return_value=None):
            where = weather.locate(settings, None, fetch=fetch)
        self.assertEqual(where, {"lat": 59.9, "lon": 10.7, "source": "ip", "name": "Oslo"})

    def test_ip_mode_never_scans(self):
        def run(*_a, **_k):
            raise AssertionError("scanned the Wi-Fi")

        settings = dict(weather.DEFAULTS, location="ip")
        where = weather.locate(settings, None, run=run, fetch=lambda *a, **k: {"latitude": 1.0, "longitude": 2.0})
        self.assertEqual(where["source"], "ip")

    def test_a_fixed_place(self):
        where = weather.geocode("43.48, -110.76")
        self.assertEqual((where["lat"], where["lon"], where["source"]), (43.48, -110.76, "fixed"))
        self.assertIsNone(weather.geocode("200, 0"))


class ForecastTests(unittest.TestCase):
    RAW = {
        "current": {"time": "2026-11-21T14:00", "temperature_2m": 7.4, "apparent_temperature": 4.9,
                    "weather_code": 2, "is_day": 1, "wind_speed_10m": 11, "relative_humidity_2m": 48},
        "daily": {"time": ["2026-11-21", "2026-11-22"], "weather_code": [2, 71], "temperature_2m_max": [9, 1],
                  "temperature_2m_min": [-3, -6], "precipitation_probability_max": [5, 80]},
        "hourly": {"time": [f"2026-11-21T{h:02}:00" for h in range(24)], "temperature_2m": list(range(24)),
                   "weather_code": [2] * 24},
    }

    def test_shape_is_what_summit_reads(self):
        data = weather.shape(self.RAW, {"lat": 1, "lon": 2, "source": "wifi"}, "Jackson", "metric",
                             now=datetime(2026, 11, 21, 21, 30, tzinfo=timezone.utc))
        self.assertEqual(data["place"]["name"], "Jackson")
        self.assertEqual(data["current"]["temperature"], 7.4)
        self.assertEqual(data["daily"][1]["rain"], 80)
        self.assertEqual(data["hourly"][0]["time"], "2026-11-21T14:00")   # from now on
        self.assertEqual(data["units"]["temperature"], "°C")
        rows = weather.rows(data)
        self.assertTrue(rows[0][0].startswith("Now   7°C  Partly cloudy"))
        self.assertIn("80% rain", rows[2][0])
        self.assertEqual(rows[2][1], "weather-snow")

    def test_the_place_name_is_kept_nearby(self):
        asked = []
        name = weather.place_name({"lat": 43.48, "lon": -110.76}, {"lat": 43.49, "lon": -110.76, "name": "Jackson"},
                                  lambda *a, **k: asked.append(a))
        self.assertEqual((name, asked), ("Jackson", []))

    def test_update_writes_the_cache(self):
        def fetch(url, params=None, body=None):
            if url == weather.IPAPI:
                return {"latitude": 43.48, "longitude": -110.76, "city": "Jackson"}
            if url == weather.OPEN_METEO:
                return self.RAW
            raise AssertionError(url)

        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "weather.json"
            with unittest.mock.patch.object(weather.shutil, "which", return_value=None):
                weather.update(dict(weather.DEFAULTS), fetch=fetch, cache=cache)
            data = json.loads(cache.read_text())
        self.assertEqual(data["place"]["source"], "ip")
        self.assertEqual(data["place"]["name"], "Jackson")


class AutoTests(unittest.TestCase):
    def test_auto_follows_summit(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "desktop-shell"
            with unittest.mock.patch.object(weather, "DESKTOP_SHELL", state):
                self.assertFalse(weather.wanted({"enabled": "auto"}))
                state.write_text("Summit\n")
                self.assertTrue(weather.wanted({"enabled": "auto"}))
                self.assertFalse(weather.wanted({"enabled": False}))

    def test_login_starts_or_stops_the_timer(self):
        calls = []
        with unittest.mock.patch.object(weather.shutil, "which", return_value="/usr/bin/systemctl"), \
                unittest.mock.patch.object(weather, "load_settings", return_value={"enabled": True}):
            weather.login(lambda cmd, **_k: calls.append(cmd))
        with unittest.mock.patch.object(weather.shutil, "which", return_value="/usr/bin/systemctl"), \
                unittest.mock.patch.object(weather, "load_settings", return_value={"enabled": False}):
            weather.login(lambda cmd, **_k: calls.append(cmd))
        self.assertEqual(calls, [["systemctl", "--user", "enable", "--now", "halcyon-weather.timer"],
                                 ["systemctl", "--user", "disable", "--now", "halcyon-weather.timer"]])


class ThemeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.patches = [unittest.mock.patch.object(theme, "SUMMIT_FILE", root / "summit.json"),
                        unittest.mock.patch.object(theme, "SUMMIT_ROFI", root / "summit-colors.rasi"),
                        unittest.mock.patch.object(theme, "DESKTOP_SHELL_FILE", root / "desktop-shell")]
        for p in self.patches:
            p.start()
        self.root = root

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def test_hyperneo_v2_runs_summit(self):
        hv2 = theme.load("hyperneo-v2")
        self.assertEqual(hv2["desktop_shell"], "Summit")
        self.assertEqual(theme.validate("hyperneo-v2", hv2), [])
        self.assertTrue(theme.resolve_wallpaper(hv2).is_file())
        self.assertEqual(theme.DESKTOP_SHELLS["Summit"], "halcyon-summit.service")

    def test_summit_gets_the_theme_and_keeps_your_pins(self):
        (self.root / "summit.json").write_text(json.dumps({"pinned": ["foot"], "bar_opacity": 0.6}))
        wallpaper = self.root / "wall.jpg"
        wallpaper.write_bytes(b"jpg")
        theme.set_desktop_shell("Summit", theme.load("hyperneo-v2"), wallpaper)
        data = json.loads((self.root / "summit.json").read_text())
        self.assertEqual(data["pinned"], ["foot"])
        self.assertEqual(data["bar_opacity"], 0.6)
        self.assertEqual(data["wallpaper"], str(wallpaper))
        self.assertEqual(data["colors"]["accent"], "#9CC0FF")
        rasi = (self.root / "summit-colors.rasi").read_text()
        self.assertIn("accent: #9CC0FF;", rasi)
        self.assertEqual((self.root / "desktop-shell").read_text().strip(), "Summit")

    def test_summit_keys_and_blur(self):
        lua = "\n".join(theme.summit_lua())
        self.assertIn('hl.bind("SUPER + Space", hl.dsp.exec_cmd("$HOME/.config/hypr/hyprland/halcyon/summit/'
                      'rofi-menu apps")', lua)
        self.assertIn('pcall(hl.unbind, "ALT + TAB")', lua)
        self.assertIn('namespace = "summit-top"', lua)
        rendered = theme.render_lua("hyperneo-v2", theme.load("hyperneo-v2"), "light", True)
        self.assertIn("rofi-menu clipboard", rendered if isinstance(rendered, str) else "\n".join(rendered))

    def test_summit_keys_work_without_the_halcyon_shell(self):
        lua = "\n".join(theme.summit_lua())
        # Super alone opens the apps on release (upstream's press bind opened fuzzel and ate Super+W and the rest).
        self.assertIn('pcall(hl.unbind, "SUPER + SUPER_L")', lua)
        self.assertIn('hl.bind("SUPER + SUPER_L", hl.dsp.exec_cmd("$HOME/.config/hypr/hyprland/halcyon/summit/'
                      'rofi-menu apps"), { release = true })', lua)
        self.assertIn('hl.bind("SUPER + SHIFT + T", hl.dsp.exec_cmd("qs -c Summit ipc call summit themes")', lua)
        self.assertIn('hl.bind("CTRL + SUPER + SHIFT + T", hl.dsp.exec_cmd("qs -c Summit ipc call summit themes")', lua)
        self.assertIn("rofi-menu keys", lua)
        self.assertNotIn('"SUPER + W"', lua)        # the browser stays Halcyon's
        self.assertIn('namespace = "summit-themes" }, blur = true', lua)
        self.assertIn('match = { class = "halcyon-forecast" }', lua)
        mac = "\n".join(theme.macshell_lua())
        self.assertIn('hl.bind("SUPER + SUPER_L", hl.dsp.exec_cmd("qs -c MacShell ipc call spotlight toggle"), '
                      '{ release = true })', mac)

    def test_the_theme_menu_opens_the_running_shells_picker(self):
        calls = []

        def run(cmd, **_k):
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        (self.root / "desktop-shell").write_text("Summit\n")
        with unittest.mock.patch.object(theme.subprocess, "run", run), \
                unittest.mock.patch.object(theme.shutil, "which", return_value="/usr/bin/qs"):
            self.assertEqual(theme.cmd_menu([]), 0)
        self.assertEqual(calls, [["qs", "-c", "Summit", "ipc", "call", "summit", "themes"]])

    def test_macshell_opens_its_theme_picker(self):
        lua = "\n".join(theme.macshell_lua())
        self.assertIn('hl.bind("SUPER + SHIFT + T", hl.dsp.exec_cmd("qs -c MacShell ipc call themes toggle")', lua)
        self.assertIn('pcall(hl.unbind, "SUPER + SHIFT + T")', lua)
        bar = (MACSHELL / "MacBar.qml").read_text()
        self.assertIn('target: "themes"', bar)
        self.assertIn('WlrLayershell.namespace: "macthemes"', bar)
        self.assertIn('[root.themeTool, "list", "--json"]', bar)
        self.assertIn('"SUPER + SHIFT + T"', (MACSHELL / "macshell.lua").read_text())


class ShellTests(unittest.TestCase):
    def run_shell(self, shell, *args):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "state/halcyon").mkdir(parents=True)
            (tmp / "state/halcyon/desktop-shell").write_text(shell + "\n")
            env = {"PATH": "/usr/bin:/bin", "XDG_STATE_HOME": str(tmp / "state"), "HOME": str(tmp),
                   "HYPRLAND_INSTANCE_SIGNATURE": "test"}
            res = subprocess.run(["sh", str(HALCYON / "desktop-shell"), *args], env=env, capture_output=True, text=True)
            return res.stdout.strip()

    def test_summit_unit(self):
        self.assertEqual(self.run_shell("Summit"), "Summit")
        self.assertEqual(self.run_shell("Summit", "unit"), "halcyon-summit.service")

    def test_one_shell_at_a_time(self):
        for unit, others in (("halcyon-summit.service", ("halcyon-quickshell.service", "halcyon-macshell.service")),
                             ("halcyon-quickshell.service", ("halcyon-summit.service",)),
                             ("halcyon-macshell.service", ("halcyon-summit.service",))):
            conflicts = next(line for line in (UNITS / unit).read_text().splitlines() if line.startswith("Conflicts="))
            for other in others:
                self.assertIn(other, conflicts, unit)
        self.assertIn("ExecStart=/usr/bin/env qs -c Summit", (UNITS / "halcyon-summit.service").read_text())
        self.assertIn("halcyon_weather.py update", (UNITS / "halcyon-weather.service").read_text())

    def test_summit_power_menu_and_lock(self):
        desk = (HALCYON / "desktop-shell").read_text()
        self.assertIn('[ "$shell" = Summit ] && exec "$(dirname -- "$0")/summit/rofi-menu" power', desk)
        self.assertIn('= Summit ]; then\n    pidof hyprlock >/dev/null || exec hyprlock', (HALCYON / "lock").read_text())
        self.assertIn("--what=handle-power-key", (SUMMIT / "shell.qml").read_text())

    def test_rofi_menu(self):
        menu = HALCYON / "summit/rofi-menu"
        self.assertTrue(os.access(menu, os.X_OK))
        self.assertEqual(subprocess.run(["bash", "-n", str(menu)]).returncode, 0)
        with tempfile.TemporaryDirectory() as tmp:
            bin_ = Path(tmp)
            (bin_ / "rofi").write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$LOG"\n')
            (bin_ / "pkill").write_text("#!/bin/sh\nexit 1\n")
            for f in bin_.iterdir():
                f.chmod(0o755)
            log = bin_ / "log"
            state = bin_ / "state/halcyon"
            state.mkdir(parents=True)
            (state / "summit-colors.rasi").write_text("* { accent: #123456; }\n")
            env = {"PATH": f"{bin_}:/usr/bin:/bin", "LOG": str(log), "HOME": tmp, "XDG_STATE_HOME": str(bin_ / "state")}
            subprocess.run(["bash", str(menu), "apps"], env=env, check=True)
            args = log.read_text().splitlines()
        self.assertEqual(args[:2], ["-config", str(HALCYON / "summit/summit.rasi")])
        self.assertIn("* { accent: #123456; }", args)
        self.assertEqual(args[-4:], ["-show", "drun", "-p", "apps"])


class FilesTests(unittest.TestCase):
    def test_glass_everywhere_without_edges(self):
        glass = (SUMMIT / "common/Glass.qml").read_text()
        self.assertNotIn("border.width", glass)               # no hairline edge
        for name in ("common/Pill.qml", "dock/Dock.qml", "dock/ToolTipLabel.qml", "popups/Calendar.qml",
                     "popups/ThemePicker.qml"):
            self.assertIn("Glass {", (SUMMIT / name).read_text(), name)
        dock = (SUMMIT / "dock/Dock.qml").read_text()
        self.assertIn("implicitHeight: 64 + Theme.gap + 44", dock)   # room for the app's name above the strip
        rasi = (HALCYON / "summit/summit.rasi").read_text()
        self.assertIn("border: 0;", rasi)

    def test_summit_files(self):
        for name in ("shell.qml", "common/Theme.qml", "bar/TopBar.qml", "dock/Dock.qml", "services/Weather.qml"):
            self.assertTrue((SUMMIT / name).is_file(), name)
        self.assertIn('"/halcyon/weather.json"', (SUMMIT / "services/Weather.qml").read_text())

    def test_forecast_window(self):
        crate = ROOT / "tools/halcyon-forecast"
        self.assertTrue((crate / "Cargo.lock").is_file())
        self.assertIn('iced = { version = "0.14"', (crate / "Cargo.toml").read_text())
        self.assertTrue((crate / "assets/weather-icons.ttf").stat().st_size < 16000)
        self.assertTrue((ROOT / "licenses/Apache-2.0.txt").is_file())
        pkg = (ROOT / "sdata/dist-arch/illogical-impulse-summit/PKGBUILD").read_text()
        self.assertIn("tools/halcyon-forecast", pkg)
        self.assertIn("rofi", pkg)

    def test_weather_command(self):
        self.assertIn('argv[0] == "weather"', (HALCYON / "halcyon-theme").read_text())


if __name__ == "__main__":
    unittest.main()


class WallAndPickerTests(unittest.TestCase):
    def test_tiled_windows_are_held_at_the_wall(self):
        plus = (HALCYON / "plus.lua").read_text()
        caps = (HALCYON / "compositor.lua").read_text()
        self.assertIn('C.holdTiled = hasOption("plus:hold_tiled")', caps)
        self.assertIn('C.snapGlide = hasOption("plus:snap_glide")', caps)
        self.assertIn("if caps.holdTiled then\n    hl.config({ plus = { hold_tiled = true } })", plus)
        self.assertIn("if caps.snapGlide then\n    hl.config({ plus = { snap_glide = 180 } })", plus)

    def test_the_halcyon_theme_picker_keeps_your_selection(self):
        picker = (ROOT / "dots/.config/quickshell/ii/modules/ii/themePicker/ThemePicker.qml").read_text()
        # Only the first list after opening selects the active theme; previews are tried once per opening.
        self.assertIn('const kept = root.fresh ? "" : (root.themes[root.selected]?.id ?? "");', picker)
        self.assertIn("if (!root.previewsTried && root.themes.some(", picker)
        self.assertIn("onPositionChanged: card.hovered()", picker)
        self.assertNotIn("onEntered: card.hovered()", picker)

    def test_summit_moves(self):
        self.assertIn("Easing.OutBack", (SUMMIT / "common/Pill.qml").read_text())          # the bar drops in
        self.assertIn("SpringAnimation", (SUMMIT / "bar/Workspaces.qml").read_text())     # dots stretch
        dock = (SUMMIT / "dock/Dock.qml").read_text()
        self.assertIn("bounce.restart()", dock)                                            # a launch bounces
        self.assertIn("onPageChanged", (SUMMIT / "popups/ThemePicker.qml").read_text())   # pages slide


class SummitFixesTests(unittest.TestCase):
    def test_moving_parts_keep_their_input_region(self):
        # A Translate on a masked item left the window's input region behind: only part of it took clicks.
        self.assertNotIn("transform: Translate", (SUMMIT / "common/Pill.qml").read_text())
        dock = (SUMMIT / "dock/Dock.qml").read_text()
        self.assertIn("bottomMargin: Theme.gap - rise", dock)
        strip = dock.split("id: strip")[1].split("Row {")[0]
        self.assertNotIn("transform:", strip)
        self.assertEqual((SUMMIT / "bar/TopBar.qml").read_text().count("topMargin: Theme.gap + "), 3)

    def test_icons_come_with_summit(self):
        font = SUMMIT / "assets/fonts/SummitSymbols.ttf"
        self.assertTrue(100_000 < font.stat().st_size < 400_000)
        theme = (SUMMIT / "common/Theme.qml").read_text()
        self.assertIn('source: Qt.resolvedUrl("../assets/fonts/SummitSymbols.ttf")', theme)
        self.assertIn('font: "Summit Symbols 15";', (HALCYON / "summit/summit.rasi").read_text())
        self.assertIn("fc-cache -f", (HALCYON / "summit/rofi-menu").read_text())

    def test_rofi_does_not_follow_the_pointer(self):
        rasi = (HALCYON / "summit/summit.rasi").read_text()
        self.assertIn("hover-select: false;", rasi)
        self.assertIn("scroll-method: 0;", rasi)

    def test_glass_is_neutral(self):
        self.assertIn("Theme.alpha(Theme.glass, root.tint)", (SUMMIT / "common/Glass.qml").read_text())
        self.assertEqual(theme.neutral("#101A2C"), "#1E1E1E")
        self.assertIn("bg-alpha: #1E1E1E8C;", theme.summit_rofi(theme.summit_colours(theme.load("hyperneo-v2"))))

    def test_battery_opens_its_popup(self):
        status = (SUMMIT / "bar/Status.qml").read_text()
        self.assertIn("onClicked: root.batteryClicked()", status)
        popup = (SUMMIT / "popups/BatteryPopup.qml").read_text()
        self.assertIn("PowerProfiles.profile = mode.modelData.profile", popup)
        self.assertIn('"/halcyon_saver.py", "toggle"', popup)
