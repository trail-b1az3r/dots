"""Halcyon on niri (the `niri` branch): niri's config, the theme's look written for it, the shell started and locked
the niri way. Run: python3 -m unittest discover -s tests"""

import importlib.machinery
import importlib.util
import re
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "dots/.config"
HALCYON = CONFIG / "hypr/hyprland/halcyon"
NIRI = CONFIG / "niri/config.kdl"
_loader = importlib.machinery.SourceFileLoader("halcyon_theme_niri", str(HALCYON / "halcyon-theme"))
_spec = importlib.util.spec_from_loader("halcyon_theme_niri", _loader)
theme = importlib.util.module_from_spec(_spec)
_loader.exec_module(theme)


def balanced(text):
    """Braces and quotes balance, ignoring // comments and raw strings: what a KDL parser would trip on first."""
    text = re.sub(r'r#".*?"#', '""', text)
    depth = 0
    for line in text.splitlines():
        line = line.split("//", 1)[0] if not line.strip().startswith('"') else line
        if line.count('"') % 2:
            return False
        depth += line.count("{") - line.count("}")
        if depth < 0:
            return False
    return depth == 0


class NiriConfigTest(unittest.TestCase):
    def setUp(self):
        self.text = NIRI.read_text()

    def test_well_formed(self):
        self.assertTrue(balanced(self.text))

    def test_starts_the_halcyon_shell_and_its_helpers(self):
        self.assertIn("halcyon/desktop-shell restart", self.text)
        self.assertIn("import-environment WAYLAND_DISPLAY NIRI_SOCKET", self.text)
        self.assertIn('spawn-at-startup "hypridle"', self.text)
        self.assertIn("ILLOGICAL_IMPULSE_VIRTUAL_ENV=$HOME/.local/state/quickshell/.venv", self.text)

    def test_shell_keys_use_ipc_targets_that_exist(self):
        shell = CONFIG / "quickshell/ii"
        handlers = {}
        for qml in shell.rglob("*.qml"):
            source = qml.read_text(errors="replace")
            for match in re.finditer(r'IpcHandler \{\s*target: "(\w+)"(.*?)\n    \}', source, re.S):
                handlers.setdefault(match.group(1), set()).update(re.findall(r"function (\w+)", match.group(2)))
        calls = re.findall(r"qs -c ii ipc call (\w+) (\w+)", self.text)
        self.assertGreater(len(calls), 10)
        for target, function in calls:
            self.assertIn(target, handlers, target)
            self.assertIn(function, handlers[target], f"{target} {function}")

    def test_includes_are_optional_so_a_fresh_install_starts(self):
        self.assertIn('include optional=true "halcyon-theme.kdl"', self.text)
        self.assertIn('include optional=true "custom.kdl"', self.text)
        self.assertFalse((CONFIG / "niri/halcyon-theme.kdl").exists(), "written by halcyon-theme, not shipped")

    def test_the_installer_never_syncs_the_folder(self):
        legacy = (ROOT / "sdata/subcmd-install/3.files-legacy.sh").read_text()
        self.assertIn("! -name 'niri'", legacy)
        self.assertIn('install_file__auto_backup "dots/.config/niri/config.kdl"', legacy)

    def test_units_run_under_niri_too(self):
        for name in ("halcyon-quickshell", "halcyon-uwu-agent"):
            unit = (CONFIG / f"systemd/user/{name}.service").read_text()
            self.assertIn("niri msg version", unit, name)
        self.assertNotIn("niri", (CONFIG / "systemd/user/halcyon-macshell.service").read_text())


class NiriThemeTest(unittest.TestCase):
    def test_every_theme_renders_well_formed(self):
        for theme_id in theme.theme_ids():
            text = theme.render_niri(theme_id, theme.load(theme_id), "full")
            self.assertTrue(balanced(text), theme_id)
            self.assertIn("geometry-corner-radius", text, theme_id)

    def test_gradient_border_becomes_a_gradient_ring(self):
        text = theme.render_niri("manga-ink", theme.load("manga-ink"), "full")
        self.assertRegex(text, r'active-gradient from="#[0-9A-Fa-f]{8}" to="#[0-9A-Fa-f]{8}" angle=45')

    def test_neumorph_has_no_ring_its_shadows_are_its_edges(self):
        text = theme.render_niri("neumorph", theme.load("neumorph"), "light")
        self.assertIn("focus-ring {\n        off", text)
        self.assertIn('color "#8C9AB2A6"', text)
        self.assertIn("offset x=9 y=9", text)

    def test_effects_off_drops_the_shadow(self):
        text = theme.render_niri("red-sun", theme.load("red-sun"), "off")
        self.assertIn("shadow {\n        off", text)

    def test_written_only_where_niri_is_set_up_and_reset_on_leaving(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            niri = root / "niri"
            patches = [unittest.mock.patch.object(theme, name, value) for name, value in (
                ("NIRI_DIR", niri), ("NIRI_THEME", niri / "halcyon-theme.kdl"),
                ("THEME_LUA", root / "theme.lua"), ("SCREEN_SHADER", root / "shader.frag"),
                ("ACTIVE_FILE", root / "active"), ("SHELL_CONFIG", root / "config.json"),
                ("SHELL_RESTORE", root / "restore.json"))]
            for patch in patches:
                patch.start()
            try:
                theme.write_window_style("hsr", theme.load("hsr"))
                self.assertFalse(niri.exists(), "no niri, nothing written")
                niri.mkdir()
                theme.write_window_style("hsr", theme.load("hsr"))
                self.assertIn("Star Rail", (niri / "halcyon-theme.kdl").read_text())
                theme.leave_theme()
                self.assertEqual((niri / "halcyon-theme.kdl").read_text(), theme.NIRI_NO_THEME)
            finally:
                for patch in patches:
                    patch.stop()

    def test_macshell_stays_off_on_niri(self):
        with unittest.mock.patch.object(theme, "hyprland_running", return_value=False), \
                unittest.mock.patch.object(theme, "niri_running", return_value=True), \
                unittest.mock.patch.object(theme, "DESKTOP_SHELL_FILE", Path(tempfile.mkdtemp()) / "desktop-shell"), \
                unittest.mock.patch.object(theme, "seed_macshell"), \
                unittest.mock.patch.object(theme, "notify") as notify, \
                unittest.mock.patch.object(theme.shutil, "which", return_value="/usr/bin/systemctl"), \
                unittest.mock.patch.object(theme.subprocess, "run") as run:
            run.return_value = unittest.mock.Mock(returncode=3)
            theme.set_desktop_shell("MacShell", {}, None)
        started = [c.args[0] for c in run.call_args_list if "start" in c.args[0]]
        self.assertEqual(started, [["systemctl", "--user", "--no-block", "start", "halcyon-quickshell.service"]])
        notify.assert_called_once()


class NiriLockTest(unittest.TestCase):
    def test_the_lock_uses_the_shell_ipc_on_niri(self):
        lock = (HALCYON / "lock").read_text()
        self.assertIn('if [ -n "${NIRI_SOCKET:-}" ]; then', lock)
        self.assertIn("qs -c ii ipc call lock activate", lock)


if __name__ == "__main__":
    unittest.main()
