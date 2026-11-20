"""The Liquid Glass theme runs MacShell (github.com/0-ss/MacShell, MIT) in place of the Halcyon shell: halcyon-theme
picks the desktop shell, halcyon/desktop-shell starts it, halcyon/lock locks with its lock screen. Run:
python3 -m unittest discover -s tests"""

import importlib.machinery
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "dots/.config"
HALCYON = CONFIG / "hypr/hyprland/halcyon"
_loader = importlib.machinery.SourceFileLoader("halcyon_theme_macshell", str(HALCYON / "halcyon-theme"))
_spec = importlib.util.spec_from_loader("halcyon_theme_macshell", _loader)
theme = importlib.util.module_from_spec(_spec)
_loader.exec_module(theme)


class BundleTest(unittest.TestCase):
    def test_macshell_and_maclock_are_bundled_with_their_licence(self):
        for folder in ("quickshell/MacShell", "quickshell/MacLock", "hypr-macshell"):
            licence = (CONFIG / folder / "LICENSE").read_text()
            self.assertIn("MIT License", licence, folder)
        self.assertTrue((CONFIG / "quickshell/MacShell/shell.qml").is_file())
        self.assertTrue((CONFIG / "quickshell/MacLock/lock-via-ipc.sh").is_file())
        # The shaders ship compiled, so the glass works without qsb.
        self.assertTrue((CONFIG / "quickshell/MacShell/liquidglass.frag.qsb").is_file())
        self.assertIn("MacShell", (ROOT / "CREDITS.md").read_text())

    def test_the_two_shells_never_run_together(self):
        units = CONFIG / "systemd/user"
        mac = (units / "halcyon-macshell.service").read_text()
        ii = (units / "halcyon-quickshell.service").read_text()
        self.assertIn("Conflicts=halcyon-quickshell.service", mac)
        self.assertIn("Conflicts=halcyon-macshell.service", ii)
        self.assertIn("ExecStart=/usr/bin/env qs -c MacShell", mac)
        # Apps opened from the Dock survive a shell restart, and quit when the session ends.
        self.assertIn("KillMode=process", mac)
        self.assertIn("ExecStopPost=%h/.config/hypr/hyprland/halcyon/session-end", mac)

    def test_hyprland_starts_whichever_shell_the_theme_wants(self):
        init = (HALCYON / "init.lua").read_text()
        self.assertIn("halcyon/desktop-shell restart", init)
        self.assertNotIn("systemctl --user restart halcyon-quickshell.service", init)

    def test_the_lock_goes_through_the_running_shell(self):
        idle = (CONFIG / "hypr/hypridle.conf").read_text()
        self.assertIn("$lock_cmd = ~/.config/hypr/hyprland/halcyon/lock", idle)


class ThemeTest(unittest.TestCase):
    def test_liquid_glass_is_valid_and_runs_macshell(self):
        data = theme.load("liquid-glass")
        self.assertEqual(data["desktop_shell"], "MacShell")
        self.assertTrue(theme.resolve_wallpaper(data).is_file())

    def test_an_unknown_desktop_shell_is_refused(self):
        data = json.loads((HALCYON / "themes/liquid-glass.json").read_text())
        data["desktop_shell"] = "waybar"
        self.assertTrue(any("desktop_shell" in p for p in theme.validate("x", data)))

    def test_theme_lua_binds_macshell_keys_over_the_halcyon_shell(self):
        data = theme.load("liquid-glass")
        lua = theme.render_lua("liquid-glass", data, "light", False)
        self.assertIn('pcall(hl.unbind, "SUPER + Space")', lua)
        self.assertIn('hl.bind("SUPER + Space", hl.dsp.exec_cmd("qs -c MacShell ipc call spotlight toggle")', lua)
        self.assertIn('namespace = "macdock"', lua)
        # The theme menu stays reachable, to come back.
        self.assertNotIn("CTRL + SUPER + SHIFT + T", lua)
        # A Halcyon-shell theme has none of it.
        other = theme.render_lua("fractured-glass", theme.load("fractured-glass"), "light", False)
        self.assertNotIn("MacShell", other)


class SetDesktopShellTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.state = self.root / "state/desktop-shell"
        self.patches = [
            unittest.mock.patch.object(theme, "DESKTOP_SHELL_FILE", self.state),
            unittest.mock.patch.object(theme, "CONFIG", self.root / "config"),
            unittest.mock.patch.object(theme, "hyprland_running", return_value=False),
        ]
        for patch in self.patches:
            patch.start()

    def tearDown(self):
        for patch in self.patches:
            patch.stop()
        self.tmp.cleanup()

    def test_macshell_is_recorded_and_its_settings_seeded(self):
        wallpaper = self.root / "wall.jpg"
        wallpaper.write_bytes(b"jpg")
        theme.set_desktop_shell("MacShell", {"mode": "dark"}, wallpaper)
        self.assertEqual(self.state.read_text().strip(), "MacShell")
        bar = json.loads((self.root / "config/macbar/settings.json").read_text())
        dock = json.loads((self.root / "config/macdock/settings.json").read_text())
        self.assertEqual(bar["wallpaperPath"], str(wallpaper))
        self.assertEqual(dock["wallpaperPath"], str(wallpaper))
        self.assertEqual(bar["appearanceMode"], "dark")
        self.assertIn("terminal", bar)

    def test_your_macshell_settings_are_kept(self):
        path = self.root / "config/macbar/settings.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"appearanceMode": "light", "terminal": "foot", "wallpaperPath": "/old.png"}))
        wallpaper = self.root / "wall.jpg"
        wallpaper.write_bytes(b"jpg")
        theme.set_desktop_shell("MacShell", {"mode": "dark"}, wallpaper)
        bar = json.loads(path.read_text())
        self.assertEqual(bar["appearanceMode"], "light")
        self.assertEqual(bar["terminal"], "foot")
        self.assertEqual(bar["wallpaperPath"], str(wallpaper))

    def test_back_to_the_halcyon_shell(self):
        theme.set_desktop_shell("MacShell", {}, None)
        theme.set_desktop_shell("ii")
        self.assertFalse(self.state.exists())

    def test_the_running_shell_is_left_alone(self):
        with unittest.mock.patch.object(theme, "hyprland_running", return_value=True), \
                unittest.mock.patch.object(theme.shutil, "which", return_value="/usr/bin/systemctl"), \
                unittest.mock.patch.object(theme.subprocess, "run") as run:
            run.return_value = subprocess.CompletedProcess([], 0)
            theme.set_desktop_shell("ii")
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(commands, [["systemctl", "--user", "is-active", "--quiet", "halcyon-quickshell.service"]])

    def test_switching_starts_the_other_unit_without_waiting(self):
        with unittest.mock.patch.object(theme, "hyprland_running", return_value=True), \
                unittest.mock.patch.object(theme.shutil, "which", return_value="/usr/bin/systemctl"), \
                unittest.mock.patch.object(theme, "set_wallpaper_awww"), \
                unittest.mock.patch.object(theme.subprocess, "run") as run:
            run.return_value = subprocess.CompletedProcess([], 3)
            theme.set_desktop_shell("MacShell", {}, None)
        self.assertIn(["systemctl", "--user", "--no-block", "start", "halcyon-macshell.service"],
                      [call.args[0] for call in run.call_args_list])


class DesktopShellScriptTest(unittest.TestCase):
    def run_script(self, state, *args):
        with tempfile.TemporaryDirectory() as tmp:
            if state is not None:
                Path(tmp, "halcyon").mkdir()
                Path(tmp, "halcyon/desktop-shell").write_text(state + "\n")
            env = dict(os.environ, XDG_STATE_HOME=tmp)
            done = subprocess.run([str(HALCYON / "desktop-shell"), *args], capture_output=True, text=True,
                                  env=env, check=False)
        return done.stdout.strip()

    def test_default_is_the_halcyon_shell(self):
        self.assertEqual(self.run_script(None), "ii")
        self.assertEqual(self.run_script(None, "unit"), "halcyon-quickshell.service")

    def test_macshell(self):
        self.assertEqual(self.run_script("MacShell"), "MacShell")
        self.assertEqual(self.run_script("MacShell", "unit"), "halcyon-macshell.service")

    def test_anything_else_is_the_halcyon_shell(self):
        self.assertEqual(self.run_script("rm -rf ~", "unit"), "halcyon-quickshell.service")


if __name__ == "__main__":
    unittest.main()
