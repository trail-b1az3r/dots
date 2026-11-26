"""Summit's side menu, hypr mode animations, notifications and their importance model, its settings page, fonts and
game mode. Run: python3 -m unittest discover -s tests"""

from __future__ import annotations

import hashlib
import importlib.machinery
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HALCYON = ROOT / "dots/.config/hypr/hyprland/halcyon"
SUMMIT = ROOT / "dots/.config/quickshell/Summit"
II = ROOT / "dots/.config/quickshell/ii"
MODEL = ROOT / "tools/summit-importance"
sys.path.insert(0, str(HALCYON))

import halcyon_fonts as fonts  # noqa: E402

_loader = importlib.machinery.SourceFileLoader("halcyon_theme_side", str(HALCYON / "halcyon-theme"))
_spec = importlib.util.spec_from_loader("halcyon_theme_side", _loader)
theme = importlib.util.module_from_spec(_spec)
_loader.exec_module(theme)


def read(path: str) -> str:
    return (SUMMIT / path).read_text(encoding="utf-8")


# Runs Summit's importance.js (a QML JavaScript library) in node: judge(model, notification, threshold) per line.
JUDGE = r"""
const fs = require("fs"), vm = require("vm");
const src = fs.readFileSync(process.argv[1], "utf8").replace(/^\.pragma library\s*$/m, "");
const m = { exports: {} };
vm.runInNewContext(src, { module: m, Math, JSON, Object, String, Infinity });
const model = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const out = [];
for (const line of fs.readFileSync(0, "utf8").split("\n").filter(Boolean))
  out.push(JSON.stringify(m.exports.judge(model, JSON.parse(line), Number(process.argv[3]))));
process.stdout.write(out.join("\n") + "\n");
"""


def judge(rows: list[dict], threshold: float = 0.6) -> list[dict]:
    text = "\n".join(json.dumps(r) for r in rows) + "\n"
    done = subprocess.run(["node", "-e", JUDGE, str(SUMMIT / "services/importance.js"),
                           str(SUMMIT / "assets/model/importance.json"), str(threshold)],
                          input=text, capture_output=True, text=True, check=True)
    return [json.loads(line) for line in done.stdout.splitlines()]


class SideMenuTests(unittest.TestCase):
    def test_the_side_menu_has_what_the_halcyon_shells_sidebar_has(self):
        menu = read("side/SideMenu.qml")
        for part in ("Header {", "Sliders {", "Toggles {", "NotificationList {", "BottomGroup {", "WifiPage {",
                     "BluetoothPage {", "SoundPage {"):
            self.assertIn(part, menu)
        self.assertIn('WlrLayershell.namespace: "summit-sidemenu"', menu)
        self.assertIn("HyprlandFocusGrab {", menu)                      # a click outside closes it
        self.assertIn("Keys.onEscapePressed", menu)
        bottom = read("side/BottomGroup.qml")
        for tab in ("MonthView {", "TodoList {", "TimerView {"):
            self.assertIn(tab, bottom)
        # The same to-do list as the Halcyon shell's.
        self.assertIn('"/quickshell/user/todo.json"', read("side/TodoList.qml"))
        toggles = read("side/Toggles.qml")
        for name in ('"Wi-Fi"', '"Bluetooth"', '"Sound"', '"Mic"', '"Silent"', '"Night light"', '"Awake"', '"Game"',
                     '"Super saver"', '"Colour"', '"Screenshot"'):
            self.assertIn(name, toggles)

    def test_it_opens_from_the_bars_right_group_and_the_right_edge(self):
        bar = read("bar/TopBar.qml")
        self.assertIn("onClicked: SummitState.toggleSideMenu(bar.modelData)", bar)
        self.assertIn("clickable: true", bar)
        self.assertIn("property bool clickable: false", read("common/Pill.qml"))
        edge = read("side/EdgeTrigger.qml")
        # Only the rightmost screen's right edge, after a moment, and never over a fullscreen window.
        self.assertIn("s.x + s.width > best.x + best.width", edge)
        self.assertIn("interval: Prefs.edgeDelay", edge)
        self.assertIn("active: Prefs.edgeOpensMenu && root.rightmost !== null && !root.fullscreen", edge)
        self.assertIn("implicitWidth: 1", edge)
        self.assertIn("SideMenu {}", read("shell.qml"))
        self.assertIn("EdgeTrigger {}", read("shell.qml"))

    def test_brightness_on_the_left_is_the_halcyon_shells_slider(self):
        bar = read("bar/TopBar.qml")
        self.assertIn("BrightnessButton {", bar)
        self.assertIn("Brightness.step(Brightness.forScreen(bar.modelData)", bar)   # scrolling the launcher too
        slider = read("common/Slider.qml")
        self.assertIn("markIcon", slider)
        popup = read("popups/BrightnessPopup.qml")
        self.assertIn('markIcon: root.monitor?.available ? "wb_twilight" : ""', popup)
        service = read("services/Brightness.qml")
        # Backlight above 30%, hyprsunset's gamma below it; brightnessctl for the panel, ddcutil for monitors.
        self.assertIn("readonly property real split: 0.3", service)
        self.assertIn("hyprctl hyprsunset gamma", service)
        self.assertIn('"brightnessctl", "--class", "backlight", "s"', service)
        self.assertIn('"ddcutil", "-b", monitor.bus, "setvcp", "10"', service)

    def test_the_singleton_is_not_named_state(self):
        # QtQuick has a State type: a singleton of that name was undefined everywhere.
        self.assertFalse((SUMMIT / "services/State.qml").exists())
        self.assertTrue((SUMMIT / "services/SummitState.qml").is_file())

    def test_the_timer_outlives_the_menu(self):
        self.assertIn("property bool timerRunning", read("services/SummitState.qml"))
        self.assertIn("SummitState.timerRunning", read("side/TimerView.qml"))

    def test_glass_layers_are_blurred(self):
        lua = "\n".join(theme.summit_lua())
        for name in ("summit-sidemenu", "summit-notifications", "summit-banner"):
            self.assertIn(f'namespace = "{name}"', lua)
        self.assertNotIn('namespace = "summit-hyprframe"', lua)


class HyprModeTests(unittest.TestCase):
    def test_the_mode_animates_round_the_screens_on_the_bar_and_in_the_card(self):
        frame = read("popups/HyprFrame.qml")
        self.assertIn('WlrLayershell.namespace: "summit-hyprframe"', frame)
        self.assertIn("mask: Region {}", frame)                       # clicks go through
        self.assertIn("readonly property bool wanted: HyprModeState.active && Prefs.hyprModeGlow", frame)
        self.assertIn("loops: Animation.Infinite", frame)             # it breathes while on
        chip = read("bar/HyprChip.qml")
        self.assertIn("readonly property bool on: HyprModeState.active", chip)
        self.assertIn("HyprChip {", read("bar/TopBar.qml"))
        card = read("popups/HyprMode.qml")
        self.assertIn("PauseAnimation { duration: 90 + entry.index * 32 }", card)   # keys arrive in turn
        self.assertIn("function onEntriesChanged() { pop.restart(); }", card)
        self.assertIn("delegate: HyprFrame {}", read("shell.qml"))


class NotificationTests(unittest.TestCase):
    def test_summit_is_the_notification_server(self):
        notifs = read("services/Notifs.qml")
        self.assertIn("NotificationServer {", notifs)
        self.assertIn('import "importance.js" as Importance', notifs)
        self.assertIn("if (Prefs.doNotDisturb)", notifs)
        self.assertIn("if (!root.fullscreenInFront())", notifs)
        self.assertIn("Component.onCompleted: Notifs.count", read("shell.qml"))

    def test_the_banner_opens_sideways_under_the_clock_and_fades_after_three_seconds(self):
        banner = read("popups/ImportantBanner.qml")
        self.assertIn("anchors.top: true", banner)
        self.assertIn("width: 44 + (window.fullWidth - 44) * window.openness", banner)
        self.assertIn("duration: 3000", banner)
        self.assertIn('NumberAnimation { target: window; property: "shown"; to: 0', banner)

    def test_the_settings_page_turns_the_model_off(self):
        self.assertIn("data.notifications?.important_banner ?? true", read("services/Prefs.qml"))
        self.assertIn('page.set("notifications.important_banner", checked)',
                      (II / "modules/settings/SummitConfig.qml").read_text())


@unittest.skipUnless(shutil.which("node"), "needs node")
class ImportanceModelTests(unittest.TestCase):
    def test_it_finds_what_matters(self):
        rows = [
            {"appName": "Messages", "summary": "PayPal", "body": "PayPal: 482913 is your security code.", "urgency": 1},
            {"appName": "Telegram", "summary": "Mum", "body": "Call me when you see this, it's about grandpa", "urgency": 1},
            {"appName": "Calendar", "summary": "Stand-up starts in 5 minutes", "body": "Room 4B", "urgency": 1},
            {"appName": "Bluesky", "summary": "Lena liked your post", "body": "", "urgency": 1},
            {"appName": "Spotify", "summary": "Holocene", "body": "Bon Iver", "urgency": 1},
            {"appName": "Steam", "summary": "Autumn Sale is live!", "body": "Huge discounts", "urgency": 1},
        ]
        verdicts = judge(rows)
        self.assertEqual([v["important"] for v in verdicts], [True, True, True, False, False, False])

    def test_urgency_decides_at_the_ends(self):
        verdicts = judge([{"appName": "x", "summary": "lol", "body": "", "urgency": 2},
                          {"appName": "x", "summary": "Your password was changed", "body": "", "urgency": 0}])
        self.assertTrue(verdicts[0]["important"])     # critical always
        self.assertFalse(verdicts[1]["important"])    # low never

    def test_the_summary_is_one_short_line(self):
        long = "Your build failed. " + "Lots of log output follows here. " * 10
        [v] = judge([{"appName": "CI", "summary": "Build failed on main", "body": long, "urgency": 1}])
        self.assertLessEqual(len(v["summary"]), 96)
        self.assertTrue(v["summary"].startswith("Build failed on main"))

    def test_it_holds_up_on_notifications_it_never_saw(self):
        rows = [json.loads(line) for line in (MODEL / "holdout.jsonl").read_text().splitlines() if line.strip()]
        verdicts = judge(rows)
        right = sum(v["important"] == bool(r["label"]) for v, r in zip(verdicts, rows))
        self.assertGreaterEqual(right / len(rows), 0.9)

    @unittest.skipUnless(importlib.util.find_spec("numpy"), "needs numpy")
    def test_the_shipped_model_is_what_training_makes(self):
        done = subprocess.run([sys.executable, str(MODEL / "train.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


class SettingsTests(unittest.TestCase):
    def test_settings_shows_summits_page_and_leaves_out_the_halcyon_shells(self):
        settings = (II / "settings.qml").read_text()
        self.assertIn("readonly property var pages: RunningShell.summit ? summitPages : allPages", settings)
        self.assertIn('component: "modules/settings/SummitConfig.qml"', settings)
        running = (II / "modules/common/RunningShell.qml").read_text()
        self.assertIn('"/halcyon/desktop-shell"', running)
        self.assertIn("blockLoading: true", running)
        halcyon = (II / "modules/settings/HalcyonConfig.qml").read_text()
        self.assertEqual(halcyon.count("visible: !RunningShell.summit"), 2)   # Star Rail, the themed launchers
        self.assertIn('RunningShell.summit ? Translation.tr("None")', halcyon)
        summit = (II / "modules/settings/SummitConfig.qml").read_text()
        self.assertIn("/halcyon/summit.json", summit)
        for key in ("notifications.popups", "notifications.do_not_disturb", "notifications.threshold",
                    "side_menu.edge", "side_menu.edge_delay", "bar.brightness", "hypr_mode.glow", "fonts.text",
                    "fonts.code"):
            self.assertIn(f'"{key}"', summit)
            # ...and Summit reads each of them.
            self.assertIn(key.split(".")[1], read("services/Prefs.qml") + read("common/Theme.qml"))


class FontTests(unittest.TestCase):
    def test_summit_sans_is_a_renamed_google_sans_flex(self):
        font = SUMMIT / "assets/fonts/SummitSans.ttf"
        self.assertTrue(200_000 < font.stat().st_size < 1_000_000)
        self.assertIn("SIL Open Font License", (SUMMIT / "assets/fonts/SummitSans-OFL.txt").read_text())
        self.assertIn('FAMILY = "Summit Sans"', (ROOT / "tools/summit-fonts/make_sans.py").read_text())
        if importlib.util.find_spec("fontTools"):
            from fontTools.ttLib import TTFont
            names = TTFont(font)["name"]
            # Its own name: "Google Sans" is Google's trademark, which a modified version may not carry.
            for name_id in (1, 4, 6, 16):
                self.assertNotIn("Google", names.getDebugName(name_id) or "", name_id)
            self.assertEqual(names.getDebugName(1), "Summit Sans")
        theme_qml = read("common/Theme.qml")
        self.assertIn('source: Qt.resolvedUrl("../assets/fonts/SummitSans.ttf")', theme_qml)
        self.assertIn('"Iosevka Nerd Font"', theme_qml)
        self.assertIn('font: "Summit Sans,Inter 11";', (HALCYON / "summit/summit.rasi").read_text())
        self.assertIn('"Iosevka Nerd Font,JetBrainsMono Nerd Font 10"', (HALCYON / "summit/rofi-menu").read_text())

    def test_the_package_carries_the_fonts(self):
        pkg = ROOT / "sdata/dist-arch/illogical-impulse-summit"
        pkgbuild = (pkg / "PKGBUILD").read_text()
        for name in ("SummitSymbols.ttf", "SummitSans.ttf", "SummitSans-OFL.txt"):
            self.assertEqual((pkg / name).read_bytes(), (SUMMIT / "assets/fonts" / name).read_bytes(), name)
            self.assertIn(hashlib.sha256((pkg / name).read_bytes()).hexdigest(), pkgbuild, name)
        for dep in ("ttf-iosevka-nerd", "hyprsunset", "brightnessctl", "hyprpicker", "hyprshot"):
            self.assertIn(f"  {dep}\n", pkgbuild)

    def test_each_cut_of_the_icons_has_its_own_family(self):
        # An older cut stays installed (the package's, ~/.local/share/fonts) under its family, and Qt and fontconfig
        # took it over the file Summit loads: the new icons showed as their names. Every cut is named for itself.
        import re
        family = re.search(r'FAMILY = "([^"]+)"', (ROOT / "tools/summit-symbols/subset.py").read_text()).group(1)
        self.assertNotEqual(family, "Summit Symbols")
        self.assertIn(f'font: "{family} 15";', (HALCYON / "summit/summit.rasi").read_text())
        self.assertIn(f'fc-list "{family}" family', (HALCYON / "summit/rofi-menu").read_text())
        if importlib.util.find_spec("fontTools"):
            from fontTools.ttLib import TTFont
            self.assertEqual(TTFont(SUMMIT / "assets/fonts/SummitSymbols.ttf")["name"].getDebugName(1), family)
        # And a name the font has no icon for draws nothing rather than the word.
        self.assertIn("text: known ? name : \"\"", read("common/Symbol.qml"))

    def test_the_new_icons_are_in_summits_font(self):
        names = (ROOT / "tools/summit-symbols/subset.py").read_text()
        for icon in ("notifications_unread", "wb_twilight", "do_not_disturb_on", "priority_high", "bluetooth"):
            self.assertIn(icon, names)

    def test_right_font_until_the_session_ends(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp) / "run"
            data = Path(tmp) / "data"
            with unittest.mock.patch.dict(os.environ, {"XDG_RUNTIME_DIR": str(runtime)}), \
                    unittest.mock.patch.object(fonts, "RIGHT_FONT_DIR", data / "fonts/halcyon-rightfont"), \
                    unittest.mock.patch.object(fonts, "tell_summit") as told, \
                    unittest.mock.patch.object(fonts.shutil, "which", return_value=None):
                self.assertEqual(fonts.main(["right-font"]), 0)
                flag = runtime / "halcyon/right-font"
                self.assertTrue(flag.is_file())                                # in $XDG_RUNTIME_DIR: gone at reboot
                self.assertTrue((data / "fonts/halcyon-rightfont/RightFont-Review-v7.ttf").is_file())
                told.assert_called_with(True)
                self.assertEqual(fonts.main(["right-font", "off"]), 0)
                self.assertFalse(flag.exists())
                told.assert_called_with(False)
        theme_qml = read("common/Theme.qml")
        self.assertIn('"/halcyon/right-font"', theme_qml)
        self.assertIn("function rightFont(on: bool): void { Theme.rightFont = on; }", read("shell.qml"))
        self.assertIn('${XDG_RUNTIME_DIR:-/tmp}/halcyon/right-font', (HALCYON / "summit/rofi-menu").read_text())


KEYS = r"""
const fs = require("fs"), vm = require("vm");
const m = { exports: {} };
vm.runInNewContext(fs.readFileSync(process.argv[1], "utf8").replace(/^\.pragma library\s*$/m, ""), { module: m, JSON, Object, String });
const binds = JSON.parse(fs.readFileSync(0, "utf8"));
const out = {};
for (const page of ["all", "hypr"])
  out[page] = m.exports.rows(binds, page).map(r => [r.category, r.caps.map(c => c.kind + ":" + c.label), r.text, r.runnable]);
out.groups = m.exports.groups(m.exports.rows(binds, "all")).map(g => g.name);
out.found = m.exports.rows(binds, "all").filter(r => m.exports.matches(r, "fn louder")).map(r => r.text);
process.stdout.write(JSON.stringify(out));
"""


@unittest.skipUnless(shutil.which("node"), "needs node")
class CheatsheetTests(unittest.TestCase):
    def keys(self, binds):
        done = subprocess.run(["node", "-e", KEYS, str(SUMMIT / "services/keys.js")], input=json.dumps(binds),
                              capture_output=True, text=True, check=True)
        return json.loads(done.stdout)

    def test_binds_become_keycaps_in_cards(self):
        out = self.keys([
            {"modmask": 64, "key": "Slash", "description": "Summit: Keybinds", "dispatcher": "exec", "arg": "x"},
            {"modmask": 69, "key": "Left", "description": "Window: Move left", "dispatcher": "movewindow", "arg": "l"},
            {"modmask": 0, "key": "XF86AudioRaiseVolume", "description": "Sound: Louder", "dispatcher": "exec", "arg": "y"},
            {"modmask": 77, "key": "W", "description": "Hyper: Weather", "dispatcher": "exec", "arg": "z"},
            {"modmask": 72, "key": "mouse:272", "description": "Window: Drag", "dispatcher": "movewindow", "arg": ""},
            {"submap": "hypr", "modmask": 0, "key": "F", "description": "Hypr mode: Fullscreen", "dispatcher": "__lua"},
            {"modmask": 64, "key": "X", "description": "", "dispatcher": "exec", "arg": "hidden"},
        ])
        self.assertEqual(out["all"][0], ["Summit", ["super:Super", ":/"], "Keybinds", True])
        self.assertEqual(out["all"][1][1], ["super:Super", "ctrl:Ctrl", "shift:Shift", ":\u2190"])
        self.assertEqual(out["all"][2][1], ["fn:Fn", ":Volume +"])                     # the media keys are Fn's
        self.assertEqual(out["all"][4][1], ["super:Super", "alt:Alt", ":Left click"])
        self.assertNotIn("Fullscreen", [r[2] for r in out["all"]])                   # hypr mode's keys: their page
        self.assertEqual(out["hypr"], [["Hyper", ["hyper:Hyper", ":W"], "Weather", True],
                                       ["Hypr mode", [":F"], "Fullscreen", True]])
        self.assertEqual(out["groups"], ["Summit", "Window", "Sound", "Hyper"])
        self.assertEqual(out["found"], ["Louder"])

    def test_the_pane_is_large_and_has_its_own_key_icons(self):
        sheet = read("popups/Cheatsheet.qml")
        self.assertIn("width: Math.min(parent.width - 96, 1640)", sheet)
        self.assertIn("WlrKeyboardFocus.Exclusive", sheet)
        self.assertIn('import "../services/keys.js" as KeyList', sheet)   # not "Keys": QtQuick's Keys handlers
        icon = read("common/KeyIcon.qml")
        for kind in ('"super"', '"ctrl"', '"shift"', '"alt"', '"fn"', '"hyper"'):
            self.assertIn(kind + ": [", icon)
        self.assertIn("KeyIcon {", read("common/KeyCap.qml"))
        self.assertIn("delegate: KeyCap {", read("popups/HyprMode.qml"))
        lua = "\n".join(theme.summit_lua())
        # Summit's pane, or Rofi's list when Summit is not running.
        self.assertIn('qs -c Summit ipc call summit keys || $HOME/.config/hypr/hyprland/halcyon/summit/rofi-menu keys', lua)
        self.assertIn('namespace = "summit-cheatsheet"', lua)


class GameModeTests(unittest.TestCase):
    def test_game_mode_is_a_state_file_hyprland_reads(self):
        lua = (HALCYON / "gamemode.lua").read_text()
        self.assertIn('"/halcyon/gamemode.json"', lua)
        self.assertIn("allow_tearing = true", lua)
        init = (HALCYON / "init.lua").read_text()
        # Before the saver, so the saver still wins where both set something.
        self.assertLess(init.index('require("hyprland.halcyon.gamemode")'), init.index('require("hyprland.halcyon.saver")'))
        self.assertIn('"/gamemode.json"', read("services/SummitState.qml"))


if __name__ == "__main__":
    unittest.main()
