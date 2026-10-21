"""One Settings window at a time: `halcyon settings` opens it, or brings the open one to the monitor you are on.
Against stand-in hyprctl and qs. Run: python3 -m unittest discover -s tests"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "dots/.config/hypr/hyprland/halcyon/halcyon-theme"
II = ROOT / "dots/.config/quickshell/ii"

SETTINGS = {"address": "0xabc", "title": "Halcyon Settings", "initialTitle": "Halcyon Settings",
            "workspace": {"id": 2, "name": "2"}, "monitor": 1}
OTHER = {"address": "0xdef", "title": "kitty", "workspace": {"id": 5, "name": "5"}}


class SettingsWindowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.bin, self.home, self.log = root / "bin", root / "home", root / "log"
        self.bin.mkdir()
        settings_qml = self.home / ".config/quickshell/ii/settings.qml"
        settings_qml.parent.mkdir(parents=True)
        settings_qml.write_text("")
        self.log.write_text("")
        self.write("qs", f'echo "qs $*" >> "{self.log}"')

    def write(self, name, body):
        path = self.bin / name
        path.write_text("#!/bin/sh\n" + body + "\n")
        path.chmod(0o755)

    def hyprctl(self, clients, active):
        self.write("hyprctl", f'''case "$1" in
  clients) echo '{json.dumps(clients)}' ;;
  activeworkspace) echo '{json.dumps(active)}' ;;
  dispatch) echo "dispatch $2" >> "{self.log}" ;;
esac''')

    def run_settings(self, hyprland=True):
        env = {"PATH": f"{self.bin}:/usr/bin:/bin", "HOME": str(self.home), "XDG_CONFIG_HOME": str(self.home / ".config"),
               "XDG_STATE_HOME": str(self.home / ".local/state")}
        if hyprland:
            env["HYPRLAND_INSTANCE_SIGNATURE"] = "test"
        done = subprocess.run([sys.executable, str(TOOL), "settings"], env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(done.returncode, 0, done.stderr)
        return [line for line in self.log.read_text().splitlines() if line]

    def test_none_open_starts_one(self):
        self.hyprctl([OTHER], {"id": 1, "name": "1"})
        self.assertEqual(self.run_settings(), [f"qs -p {self.home}/.config/quickshell/ii/settings.qml"])

    def test_open_on_another_monitor_is_brought_here_not_opened_again(self):
        self.hyprctl([OTHER, SETTINGS], {"id": 7, "name": "7"})
        self.assertEqual(self.run_settings(), [
            'dispatch hl.dsp.window.move({ workspace = "7", follow = false, window = "address:0xabc" })',
            'dispatch hl.dsp.focus({ window = "address:0xabc" })'])

    def test_open_here_is_only_focused(self):
        self.hyprctl([SETTINGS], {"id": 2, "name": "2"})
        self.assertEqual(self.run_settings(), ['dispatch hl.dsp.focus({ window = "address:0xabc" })'])

    def test_a_second_press_while_it_is_starting_opens_nothing(self):
        self.hyprctl([], {"id": 1, "name": "1"})
        self.run_settings()
        self.assertEqual(len(self.run_settings()), 1, "still one launch")

    def test_every_settings_button_goes_through_it(self):
        for path in ("modules/ii/sidebarRight/SidebarRightContent.qml", "modules/waffle/bar/StartButton.qml",
                     "modules/waffle/actionCenter/mainPage/MainPageFooter.qml"):
            self.assertIn("Directories.openSettingsCommand", (II / path).read_text(), path)
        self.assertIn("halcyon-theme settings", (ROOT / "dots/.config/hypr/hyprland/variables.lua").read_text())


if __name__ == "__main__":
    unittest.main()


class WidgetSwitchesTest(unittest.TestCase):
    def run_tool(self, home, *args):
        env = {"PATH": "/usr/bin:/bin", "HOME": home, "XDG_CONFIG_HOME": home + "/.config", "XDG_STATE_HOME": home + "/s"}
        return subprocess.run([sys.executable, str(TOOL), "widgets", *args], env=env, capture_output=True, text=True, timeout=30)

    def test_widgets_on_off_and_their_defaults(self):
        with tempfile.TemporaryDirectory() as home:
            cfg = Path(home, ".config/illogical-impulse/config.json")
            cfg.parent.mkdir(parents=True)
            cfg.write_text(json.dumps({"background": {"widgets": {"system": {"enable": False, "x": 5}}}}))
            listing = dict(line.split() for line in self.run_tool(home).stdout.splitlines())
            self.assertEqual(listing["clock"], "on", "on by default, as in Config.qml")
            self.assertEqual(listing["revolver"], "on")
            self.assertEqual(listing["lyrics"], "off")
            self.assertEqual(self.run_tool(home, "system", "toggle").stdout.strip(), "system on")
            self.assertEqual(self.run_tool(home, "nowplaying", "on").stdout.strip(), "nowPlaying on")
            self.assertEqual(self.run_tool(home, "clock", "toggle").stdout.strip(), "clock off")
            widgets = json.loads(cfg.read_text())["background"]["widgets"]
            self.assertEqual((widgets["system"], widgets["nowPlaying"]["enable"], widgets["clock"]["enable"]),
                             ({"enable": True, "x": 5}, True, False))
            self.assertNotEqual(self.run_tool(home, "toaster", "on").returncode, 0)

    def test_quick_settings_list_every_widget(self):
        quick = (II / "modules/settings/QuickConfig.qml").read_text()
        for key in ("clock", "weather", "revolver", "visualizer", "system", "nowPlaying", "lyrics"):
            self.assertIn(f'key: "{key}"', quick)


class IconsTest(unittest.TestCase):
    def test_app_icons_never_fall_back_to_the_missing_checkerboard(self):
        for path in ("modules/ii/bar/Workspaces.qml", "modules/ii/overview/OverviewWindow.qml",
                     "modules/ii/dock/DockAppButton.qml", "modules/ii/regionSelector/TargetRegion.qml"):
            text = (II / path).read_text()
            self.assertIn("AppSearch.iconSource(", text, path)
            self.assertNotIn('"image-missing")', text.replace("Prevent the \"image-missing\" icon", ""), path)
        search = (II / "services/AppSearch.qml").read_text()
        self.assertIn('"file://" + root.bundledGenericIcon', search)
        self.assertTrue((II / "assets/icons/halcyon-app-generic.svg").is_file())

    def test_halcyon_notifications_wear_the_theme(self):
        self.assertIn("halcyon-symbolic.svg", (II / "services/Notifications.qml").read_text())
        icon = (II / "modules/common/widgets/NotificationAppIcon.qml").read_text()
        self.assertIn("ColorOverlay", icon)
        self.assertIn("Appearance.colors.colOnSecondaryContainer", icon)
