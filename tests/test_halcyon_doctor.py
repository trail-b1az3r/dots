"""`halcyon doctor`: one report on updates, the revolver, the browser themes and the Wi-Fi, which runs (and says what
is wrong) even on a machine where none of them are set up. Run: python3 -m unittest discover -s tests"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THEME = ROOT / "dots/.config/hypr/hyprland/halcyon/halcyon-theme"


class DoctorTest(unittest.TestCase):
    def test_reports_every_part_in_an_empty_home(self):
        with tempfile.TemporaryDirectory() as home:
            env = {**os.environ, "HOME": home, "XDG_STATE_HOME": f"{home}/.local/state",
                   "XDG_CONFIG_HOME": f"{home}/.config", "XDG_DATA_HOME": f"{home}/.local/share",
                   "HALCYON_SYSFS": f"{home}/sys", "HALCYON_WIFI_WAIT_NM": "0"}
            done = subprocess.run([sys.executable, str(THEME), "doctor"], capture_output=True, text=True, env=env,
                                  timeout=120)
        self.assertEqual(done.returncode, 0, done.stderr)
        out = done.stdout
        for heading in ("== Updates", "== Revolver", "== Firefox and Chromium", "== Wi-Fi"):
            self.assertIn(heading, out)
        self.assertIn("No repository is recorded", out)
        self.assertIn("`halcyon doctor --fix` fixes what it can", out)


if __name__ == "__main__":
    unittest.main()
