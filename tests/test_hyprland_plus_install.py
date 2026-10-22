"""Installing a built hyprland-plus (sdata/lib/hyprland-plus-install.sh): a make install that stops part way still
leaves Hyprland in the bin folder, and a binary that isn't hyprland-plus fails. Run: python3 -m unittest discover -s tests"""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INSTALL = ROOT / "sdata/lib/hyprland-plus-install.sh"
BUILD = ROOT / "sdata/lib/hyprland-plus-build.sh"


class InstallTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.repo = self.tmp / "hyprland-plus"
        (self.repo / "build/start").mkdir(parents=True)
        self.bin = self.tmp / "bin"
        self.stubs = self.tmp / "stubs"
        self.stubs.mkdir()

    def built(self, version="hyprland-plus 0.56.2.p3 (Hyprland 0.56.2)"):
        for path, text in ((self.repo / "build/Hyprland", f'echo "{version}"'), (self.repo / "build/start/start-hyprland", "true")):
            path.write_text(f"#!/bin/sh\n{text}\n")
            path.chmod(0o755)

    def run_install(self, make_status=0):
        (self.stubs / "make").write_text(f"#!/bin/sh\nexit {make_status}\n")
        (self.stubs / "make").chmod(0o755)
        script = f'source "{INSTALL}"; hyprland_plus_install "{self.repo}" "{self.bin}"'
        return subprocess.run(["bash", "-c", script], capture_output=True, text=True,
                              env={**os.environ, "PATH": f"{self.stubs}:{os.environ['PATH']}"}, timeout=30)

    def test_installs_and_checks(self):
        self.built()
        done = self.run_install()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue((self.bin / "Hyprland").is_file())
        self.assertTrue((self.bin / "start-hyprland").is_file())
        self.assertEqual(os.readlink(self.bin / "hyprland"), "Hyprland")

    def test_a_failed_make_install_still_installs_the_binaries(self):
        self.built()
        done = self.run_install(make_status=2)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("make install stopped", done.stderr)
        self.assertTrue((self.bin / "Hyprland").is_file())

    def test_nothing_built_says_so(self):
        done = self.run_install()
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("is not built", done.stderr)

    def test_not_hyprland_plus_fails(self):
        self.built("Hyprland 0.56.2")
        self.assertNotEqual(self.run_install().returncode, 0)

    def test_the_console_build_installs_the_dependencies_and_uses_it(self):
        text = BUILD.read_text()
        self.assertIn("packaging/aur/PKGBUILD", text)
        self.assertIn("pacman -T", text)
        self.assertIn("hyprland_plus_install", text)
        self.assertIn("hyprland-plus-install.log", text)


if __name__ == "__main__":
    unittest.main()
