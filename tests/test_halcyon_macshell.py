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

    def test_shell_lua_binds_macshell_keys_over_the_halcyon_shell(self):
        lua = theme.shell_lua("MacShell")
        self.assertIn('pcall(hl.unbind, "SUPER + Space")', lua)
        self.assertIn('hl.bind("SUPER + Space", hl.dsp.exec_cmd("qs -c MacShell ipc call spotlight toggle")', lua)
        self.assertIn('namespace = "macdock"', lua)
        # The theme menu stays reachable, to come back.
        self.assertNotIn("CTRL + SUPER + SHIFT + T", lua)
        # The theme's own lua has none of it: the shell you run may not be the theme's.
        self.assertNotIn("MacShell", theme.render_lua("liquid-glass", theme.load("liquid-glass"), "light", False))
        self.assertEqual(theme.shell_lua("ii"), "")


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
    def run_script(self, state, *args, hyprland=True):
        with tempfile.TemporaryDirectory() as tmp:
            if state is not None:
                Path(tmp, "halcyon").mkdir()
                Path(tmp, "halcyon/desktop-shell").write_text(state + "\n")
            env = dict(os.environ, XDG_STATE_HOME=tmp)
            env.pop("HYPRLAND_INSTANCE_SIGNATURE", None)
            if hyprland:
                env["HYPRLAND_INSTANCE_SIGNATURE"] = "test"
            done = subprocess.run([str(HALCYON / "desktop-shell"), *args], capture_output=True, text=True,
                                  env=env, check=False)
        return done.stdout.strip()

    def test_default_is_the_halcyon_shell(self):
        self.assertEqual(self.run_script(None), "ii")
        self.assertEqual(self.run_script(None, "unit"), "halcyon-quickshell.service")

    def test_macshell(self):
        self.assertEqual(self.run_script("MacShell"), "MacShell")
        self.assertEqual(self.run_script("MacShell", "unit"), "halcyon-macshell.service")

    def test_macshell_needs_hyprland(self):
        # Under niri (no Hyprland), the Halcyon shell runs whatever the theme asked for.
        self.assertEqual(self.run_script("MacShell", "unit", hyprland=False), "halcyon-quickshell.service")

    def test_anything_else_is_the_halcyon_shell(self):
        self.assertEqual(self.run_script("rm -rf ~", "unit"), "halcyon-quickshell.service")


if __name__ == "__main__":
    unittest.main()


class ShellChoiceTest(unittest.TestCase):
    """halcyon shell NAME: the desktop shell you pick, whatever the theme."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.state = self.root / "state/desktop-shell"
        self.patches = [
            unittest.mock.patch.object(theme, "DESKTOP_SHELL_FILE", self.state),
            unittest.mock.patch.object(theme, "CONFIG", self.root / "config"),
            unittest.mock.patch.object(theme, "hyprland_running", return_value=False),
            unittest.mock.patch.object(theme, "notify"),
            unittest.mock.patch.object(theme, "set_shell_value"),
            unittest.mock.patch.object(theme, "active", return_value=None),
        ]
        for patch in self.patches:
            patch.start()

    def tearDown(self):
        for patch in self.patches:
            patch.stop()
        self.tmp.cleanup()

    def test_your_choice_wins_over_the_theme(self):
        theme.cmd_shell(["glass"])
        self.assertEqual((self.root / "state/shell-choice").read_text().strip(), "Glass")
        self.assertEqual(self.state.read_text().strip(), "Glass")
        theme.set_desktop_shell("Summit", {}, None)   # a Summit theme applied afterwards
        self.assertEqual(self.state.read_text().strip(), "Glass")

    def test_auto_follows_the_theme_again(self):
        theme.cmd_shell(["glass"])
        theme.cmd_shell(["auto"])
        self.assertFalse((self.root / "state/shell-choice").exists())
        self.assertFalse(self.state.exists())

    def test_glass_writes_liquid_blur_and_glass_panels(self):
        theme.cmd_shell(["glass"])
        lua = (self.root / "state/shell.lua").read_text()
        self.assertIn("variant = 11", lua)
        self.assertIn('pcall(hl.get_config, "decoration:blur:liquid:refraction")', lua)
        self.assertIn('namespace = "bar[0-9]*" }, blur = true', lua)
        theme.set_shell_value.assert_called_with("halcyon.liquidGlass", True)
        theme.cmd_shell(["halcyon"])
        self.assertFalse((self.root / "state/shell.lua").exists())
        theme.set_shell_value.assert_called_with("halcyon.liquidGlass", False)

    def test_noctalia_needs_its_package(self):
        with unittest.mock.patch.object(theme.shutil, "which", return_value=None):
            with self.assertRaises(theme.ThemeError):
                theme.cmd_shell(["noctalia"])
        with unittest.mock.patch.object(theme.shutil, "which", return_value="/usr/bin/noctalia"):
            theme.cmd_shell(["noctalia"])
        lua = (self.root / "state/shell.lua").read_text()
        self.assertIn('hl.dsp.exec_cmd("noctalia msg panel-toggle launcher")', lua)
        self.assertIn('namespace = "noctalia-bar-.*"', lua)
        self.assertEqual(theme.DESKTOP_SHELLS["Noctalia"], "halcyon-noctalia.service")

    def test_scripts_know_every_shell(self):
        script = (HALCYON / "desktop-shell").read_text()
        for name in ("Noctalia) unit=halcyon-noctalia.service", "Glass) unit=halcyon-quickshell.service"):
            self.assertIn(name, script)
        self.assertIn("noctalia msg lock", (HALCYON / "lock").read_text())
        self.assertIn('stateHome .. "/halcyon/shell.lua"', (HALCYON / "init.lua").read_text())
        unit = (HALCYON.parents[2] / "systemd/user/halcyon-noctalia.service").read_text()
        self.assertIn("ExecStart=/usr/bin/env noctalia", unit)
        for other in ("halcyon-quickshell", "halcyon-macshell", "halcyon-summit"):
            self.assertIn("halcyon-noctalia.service", (HALCYON.parents[2] / f"systemd/user/{other}.service").read_text())
