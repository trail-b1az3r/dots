"""`halcyon oled`: hyproled's OLED burn-in care, kept on across logins, config reloads and theme changes.
Run: python3 -m unittest discover -s tests"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

HALCYON = Path(__file__).resolve().parent.parent / "dots/.config/hypr/hyprland/halcyon"
UNITS = Path(__file__).resolve().parent.parent / "dots/.config/systemd/user"
sys.path.insert(0, str(HALCYON))
import halcyon_oled as oled  # noqa: E402


class OledTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name) / "halcyon/oled.json"
        self.calls = []

        def run(cmd, **kwargs):
            self.calls.append([str(c) for c in cmd])
            return subprocess.CompletedProcess(cmd, 0, "", "")

        self.patches = [unittest.mock.patch.object(oled, "STATE", self.state),
                        unittest.mock.patch.object(oled.subprocess, "run", run),
                        unittest.mock.patch.object(oled.shutil, "which", lambda name: f"/usr/bin/{name}")]
        for patch in self.patches:
            patch.start()

    def tearDown(self):
        for patch in self.patches:
            patch.stop()
        self.tmp.cleanup()

    def hyproled_calls(self):
        return [c for c in self.calls if c[0].endswith("hyproled/hyproled")]

    def test_on_saves_the_settings_and_starts_hyproled_and_its_timer(self):
        self.assertEqual(oled.main(["on", "--pixels", "2", "--area", "0:0:1920:40", "--monitor", "1"]), 0)
        self.assertEqual(json.loads(self.state.read_text()), {"pixels": 2, "area": "0:0:1920:40", "monitor": 1})
        self.assertIn(["systemctl", "--user", "enable", "--now", "halcyon-oled.timer"], self.calls)
        self.assertEqual(self.hyproled_calls()[-1][1:], ["-o", "2", "-m", "1", "-a", "0:0:1920:40"])
        # The theme is rendered again first, so its screen shader steps aside.
        self.assertTrue(any(c[1].endswith("halcyon-theme") and c[2:] == ["refresh"] for c in self.calls))

    def test_shift_moves_the_pixels_and_does_nothing_when_off(self):
        oled.main(["shift"])
        self.assertEqual(self.hyproled_calls(), [])
        oled.main(["on"])
        oled.main(["shift"])
        self.assertEqual(self.hyproled_calls()[-1][-1], "-s")

    def test_off_turns_it_all_off(self):
        oled.main(["on"])
        oled.main(["off"])
        self.assertFalse(self.state.exists())
        self.assertIn(["systemctl", "--user", "disable", "--now", "halcyon-oled.timer"], self.calls)
        self.assertEqual(self.hyproled_calls()[-1][1:], ["off"])

    def test_bad_values_are_refused(self):
        with self.assertRaises(SystemExit):
            oled.main(["on", "--pixels", "4"])
        with self.assertRaises(SystemExit):
            oled.main(["on", "--area", "top"])
        self.assertFalse(self.state.exists())


class WiringTest(unittest.TestCase):
    def test_hyproled_is_bundled_with_its_licence(self):
        tool = HALCYON / "hyproled/hyproled"
        self.assertTrue(os.access(tool, os.X_OK))
        self.assertIn("hl.config", tool.read_text())   # the Lua-config hyproled, for Hyprland 0.57 (hyprland-plus)
        self.assertIn("BSD 3-Clause", (HALCYON / "hyproled/LICENSE").read_text())
        self.assertTrue(os.access(HALCYON / "halcyon_oled.py", os.X_OK))

    def test_a_config_reload_and_a_login_keep_it(self):
        init = (HALCYON / "init.lua").read_text()
        self.assertIn('"/halcyon/oled.json"', init)
        self.assertIn("screen_shader = oledShader", init)
        self.assertIn("halcyon_oled.py apply", init)

    def test_the_theme_steps_aside(self):
        source = (HALCYON / "halcyon-theme").read_text()
        self.assertIn('OLED_STATE = HALCYON_STATE / "oled.json"', source)
        self.assertIn("if OLED_STATE.exists():", source)
        self.assertIn('argv[0] == "oled"', source)

    def test_the_timer(self):
        service = (UNITS / "halcyon-oled.service").read_text()
        self.assertIn("ExecCondition=", service)
        self.assertIn("halcyon_oled.py shift", service)
        self.assertIn("OnUnitActiveSec=15min", (UNITS / "halcyon-oled.timer").read_text())


if __name__ == "__main__":
    unittest.main()
