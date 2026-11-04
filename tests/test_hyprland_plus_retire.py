"""With the hyprland-plus package installed, an older build of ours in /usr/local would start instead of it, and fail
once its libraries moved on (aquamarine 0.16 dropped libaquamarine.so.14): the installer moves it aside.
Run: python3 -m unittest discover -s tests"""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DETECT = ROOT / "sdata/lib/hyprland-plus-detect.sh"
STEP = (ROOT / "sdata/subcmd-install/7.hyprland-plus.sh").read_text()


class RetireLocalBuildTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.prefix = self.tmp / "local"
        (self.prefix / "bin").mkdir(parents=True)
        (self.prefix / "share/wayland-sessions").mkdir(parents=True)
        self.stubs = self.tmp / "stubs"
        self.stubs.mkdir()

    def pacman(self, installed: bool):
        (self.stubs / "pacman").write_text("#!/bin/sh\n" + ("echo hyprland-plus 0.57.1.p1-2\nexit 0\n" if installed else "exit 1\n"))
        (self.stubs / "pacman").chmod(0o755)

    def build(self, mark=b"hyprland-plus 0.57.0.p3"):
        (self.prefix / "bin/Hyprland").write_bytes(b"\x7fELF " + mark)
        (self.prefix / "bin/hyprland").symlink_to("Hyprland")
        (self.prefix / "bin/hyprctl").write_text("#!/bin/sh\n")
        (self.prefix / "bin/other").write_text("keep")
        (self.prefix / "share/wayland-sessions/hyprland.desktop").write_text("Exec=start-hyprland\n")

    def retire(self):
        env = {**os.environ, "PATH": f"{self.stubs}:{os.environ['PATH']}", "HALCYON_LOCAL_PREFIX": str(self.prefix)}
        return subprocess.run(["bash", "-c", f'source "{DETECT}"; hyprland_plus_retire_local'],
                              env=env, capture_output=True, text=True, timeout=30)

    def test_moved_aside_when_the_package_is_installed(self):
        self.pacman(True)
        self.build()
        run = self.retire()
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("is now in", run.stdout)
        self.assertFalse((self.prefix / "bin/Hyprland").exists())
        self.assertFalse((self.prefix / "bin/hyprland").is_symlink())
        self.assertTrue((self.prefix / "bin/other").exists())
        kept = next((self.prefix / "lib/hyprland-plus-retired").iterdir())
        self.assertEqual(sorted(p.name for p in (kept / "bin").iterdir()), ["Hyprland", "hyprctl", "hyprland"])
        self.assertTrue((kept / "share/wayland-sessions/hyprland.desktop").is_file())

    def test_kept_when_it_is_the_only_hyprland(self):
        self.pacman(False)
        self.build()
        self.assertEqual(self.retire().returncode, 0)
        self.assertTrue((self.prefix / "bin/Hyprland").exists())

    def test_a_stock_build_is_left_alone(self):
        self.pacman(True)
        self.build(mark=b"Hyprland 0.57.1")
        self.retire()
        self.assertTrue((self.prefix / "bin/Hyprland").exists())

    def test_the_installer_calls_it_when_the_package_is_there(self):
        branch = STEP[STEP.index("if pacman -Q hyprland-plus"):]
        branch = branch[:branch.index("fi\n")]
        self.assertIn("hyprland_plus_retire_local", branch)


if __name__ == "__main__":
    unittest.main()
