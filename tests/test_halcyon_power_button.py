"""The power button opens a power menu under either desktop shell: the Halcyon shell's own, and under MacShell (which
has none) the distribution's or wlogout, with halcyon-power-key.service holding logind's lock while MacShell runs.
Run: python3 -m unittest discover -s tests"""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HALCYON = ROOT / "dots/.config/hypr/hyprland/halcyon"
UNITS = ROOT / "dots/.config/systemd/user"


class PowerMenuTest(unittest.TestCase):
    def run_menu(self, shell, os_id="frontline", have=("frontline-power-menu", "wlogout", "qs")):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "state/halcyon").mkdir(parents=True)
            (tmp / "state/halcyon/desktop-shell").write_text(shell + "\n")
            (tmp / "os-release").write_text(f'NAME="X"\nID={os_id}\n')
            bin_ = tmp / "bin"
            bin_.mkdir()
            for name in have:
                (bin_ / name).write_text(f'#!/bin/sh\necho "{name} $*"\n')
                (bin_ / name).chmod(0o755)
            # Inside Hyprland: MacShell runs only there (the niri branch picks the Halcyon shell elsewhere).
            env = {"PATH": f"{bin_}:/usr/bin:/bin", "XDG_STATE_HOME": str(tmp / "state"),
                   "OS_RELEASE": str(tmp / "os-release"), "HOME": str(tmp), "HYPRLAND_INSTANCE_SIGNATURE": "test"}
            res = subprocess.run(["sh", str(HALCYON / "desktop-shell"), "power-menu"], env=env, capture_output=True,
                                 text=True)
            return res.returncode, res.stdout.strip()

    def test_the_halcyon_shell_opens_its_own(self):
        self.assertEqual(self.run_menu("ii"), (0, "qs -c ii ipc call session toggle"))

    def test_macshell_gets_the_distributions(self):
        self.assertEqual(self.run_menu("MacShell"), (0, "frontline-power-menu"))

    def test_elsewhere_wlogout(self):
        self.assertEqual(self.run_menu("MacShell", os_id="arch"), (0, "wlogout -p layer-shell"))
        self.assertEqual(self.run_menu("MacShell", os_id="arch", have=())[0], 1)

    def test_the_lock_follows_macshell(self):
        unit = (UNITS / "halcyon-power-key.service").read_text()
        self.assertIn("BindsTo=halcyon-macshell.service", unit)     # stops when MacShell stops or fails
        self.assertIn("--what=handle-power-key", unit)
        self.assertIn("Wants=halcyon-power-key.service", (UNITS / "halcyon-macshell.service").read_text())
        keys = (HALCYON / "keybinds.lua").read_text()
        self.assertIn('hl.bind("XF86PowerOff", hl.dsp.exec_cmd(qsIsAlive .. " || $HOME/.config/hypr/hyprland/'
                      'halcyon/desktop-shell power-menu"))', keys)


if __name__ == "__main__":
    unittest.main()
