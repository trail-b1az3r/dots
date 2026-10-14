"""`halcyon-theme migrate`: a theme applied by an older Halcyon is applied again when it was renamed or its files
changed, so settings it gained since (Red Sun turning on the revolver) take effect. Run:
python3 -m unittest discover -s tests"""

import importlib.machinery
import importlib.util
import json
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HALCYON = ROOT / "dots/.config/hypr/hyprland/halcyon"
_loader = importlib.machinery.SourceFileLoader("halcyon_theme_migrate", str(HALCYON / "halcyon-theme"))
_spec = importlib.util.spec_from_loader("halcyon_theme_migrate", _loader)
theme = importlib.util.module_from_spec(_spec)
_loader.exec_module(theme)


class MigrateTest(unittest.TestCase):
    def run_migrate(self, active, shell_theme, changed=()):
        with tempfile.TemporaryDirectory() as tmp:
            active_file = Path(tmp, "active")
            if active:
                active_file.write_text(active + "\n")
            shell = Path(tmp, "config.json")
            shell.write_text(json.dumps({"halcyon": {"theme": shell_theme}}))
            with unittest.mock.patch.object(theme, "ACTIVE_FILE", active_file), \
                    unittest.mock.patch.object(theme, "SHELL_CONFIG", shell), \
                    unittest.mock.patch.object(theme, "cmd_apply", return_value=0) as apply, \
                    unittest.mock.patch.object(theme, "update_browsers") as browsers:
                args = ["--changed", *changed] if changed else []
                self.assertEqual(theme.cmd_migrate(args), 0)
        return apply, browsers

    def test_a_renamed_theme_is_applied_under_its_new_name(self):
        apply, browsers = self.run_migrate("wallpaper-heaven-kenami", "wallpaper-heaven-kenami")
        apply.assert_called_once_with(["red-sun"])

    def test_the_shell_still_holding_the_old_name_is_enough(self):
        apply, _ = self.run_migrate("red-sun", "wallpaper-heaven-kenami")
        apply.assert_called_once_with(["red-sun"])

    def test_a_changed_theme_file_applies_it_again(self):
        apply, _ = self.run_migrate("red-sun", "red-sun",
                                    ["dots/.config/hypr/hyprland/halcyon/themes/red-sun.json"])
        apply.assert_called_once_with(["red-sun"])

    def test_nothing_changed_only_rewrites_the_browser_themes(self):
        apply, browsers = self.run_migrate("red-sun", "red-sun", ["dots/.config/hypr/hyprland/halcyon/themes/hsr.json"])
        apply.assert_not_called()
        browsers.assert_called_once()

    def test_no_theme_on(self):
        apply, browsers = self.run_migrate("", "")
        apply.assert_not_called()
        browsers.assert_called_once()

    def test_red_sun_turns_the_revolver_on(self):
        red_sun = json.loads((HALCYON / "themes/red-sun.json").read_text())
        self.assertIs(red_sun["shell_config"]["background.widgets.revolver.enable"], True)


class RevolverOnTest(unittest.TestCase):
    """The revolver is on for every theme now; the old default (off) the shell saved is turned on once."""

    def run_once(self, stored, restore=None):
        with tempfile.TemporaryDirectory() as tmp:
            shell = Path(tmp, "config.json")
            shell.write_text(json.dumps(stored))
            restore_file = Path(tmp, "shell-restore.json")
            if restore is not None:
                restore_file.write_text(json.dumps(restore))
            with unittest.mock.patch.object(theme, "SHELL_CONFIG", shell), \
                    unittest.mock.patch.object(theme, "SHELL_RESTORE", restore_file), \
                    unittest.mock.patch.object(theme, "REVOLVER_ON_MARKER", Path(tmp, "marker")):
                first = theme.migrate_revolver_on()
                data = json.loads(shell.read_text())
                # Turned off again by hand afterwards: it stays off.
                data["background"]["widgets"]["revolver"]["enable"] = False
                shell.write_text(json.dumps(data))
                second = theme.migrate_revolver_on()
                after = json.loads(shell.read_text())
                left = json.loads(restore_file.read_text()) if restore_file.exists() else None
        return first, second, data, after, left

    def test_saved_off_is_turned_on_once(self):
        first, second, data, after, _ = self.run_once({"background": {"widgets": {"revolver": {"enable": False, "x": 5}}}})
        self.assertTrue(first)
        self.assertFalse(second)
        self.assertIs(after["background"]["widgets"]["revolver"]["enable"], False, "a later choice is kept")
        self.assertEqual(after["background"]["widgets"]["revolver"]["x"], 5)

    def test_leaving_red_sun_no_longer_turns_it_off(self):
        restore = {"background.widgets.revolver.enable": {"had": True, "previous": False, "set": True},
                   "appearance.transparency.enable": {"had": True, "previous": False, "set": True}}
        _, _, _, _, left = self.run_once({"background": {"widgets": {"revolver": {"enable": True}}}}, restore)
        self.assertNotIn("background.widgets.revolver.enable", left)
        self.assertIn("appearance.transparency.enable", left, "the theme's other settings still go back")

    def test_on_by_default_in_the_shell(self):
        config = (ROOT / "dots/.config/quickshell/ii/modules/common/Config.qml").read_text()
        block = config[config.index("property JsonObject revolver: JsonObject {"):]
        self.assertIn("property bool enable: true", block[:200])

    def test_both_panel_families_load_it(self):
        qs = ROOT / "dots/.config/quickshell/ii/modules"
        self.assertIn("RevolverLoader {", (qs / "ii/background/Background.qml").read_text())
        self.assertIn("RevolverLoader {", (qs / "waffle/background/WaffleBackground.qml").read_text())


class StartupTest(unittest.TestCase):
    def test_login_and_update_run_it(self):
        self.assertIn("halcyon-theme migrate", (HALCYON / "init.lua").read_text())
        self.assertIn('"$theme_tool" migrate --changed', (HALCYON / "update").read_text())


if __name__ == "__main__":
    unittest.main()
