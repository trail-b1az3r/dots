"""Loaf as the file manager (halcyon_file_manager.py): once it is installed, folders open in it and Dolphin's pins go
to it, once, against a stand-in xdg-mime and a scratch home. Run: python3 -m unittest discover -s tests"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "dots/.config/hypr/hyprland/halcyon/halcyon_file_manager.py"


class FileManagerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        home = Path(self.tmp.name)
        self.bin = home / "bin"
        self.bin.mkdir()
        self.mime = home / "mime"
        (self.bin / "xdg-mime").write_text(f"""#!/bin/sh
if [ "$1" = default ]; then echo "$2" > "{self.mime}"; else cat "{self.mime}" 2>/dev/null; fi
""")
        (self.bin / "xdg-mime").chmod(0o755)
        self.apps = home / ".local/share/applications"
        self.apps.mkdir(parents=True)
        (self.apps / "org.kde.dolphin.desktop").write_text("[Desktop Entry]\n")
        self.config = home / ".config/illogical-impulse/config.json"
        self.config.parent.mkdir(parents=True)
        self.config.write_text(json.dumps({"dock": {"pinnedApps": ["org.kde.dolphin", "kitty"]},
                                           "launcher": {"pinnedApps": ["org.kde.dolphin", "firefox"]}}))
        self.env = {**os.environ, "HOME": str(home), "PATH": f"{self.bin}:/usr/bin:/bin",
                    "XDG_CONFIG_HOME": str(home / ".config"), "XDG_DATA_HOME": str(home / ".local/share"),
                    "XDG_STATE_HOME": str(home / ".local/state")}

    def install_loaf(self):
        (self.bin / "loaf").write_text("#!/bin/sh\n")
        (self.bin / "loaf").chmod(0o755)
        (self.apps / "loaf.desktop").write_text("[Desktop Entry]\nExec=loaf %U\n")

    def run_tool(self, *args):
        return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True, env=self.env)

    def test_nothing_happens_without_loaf(self):
        self.run_tool("login")
        self.assertFalse(self.mime.exists())
        self.assertIn("org.kde.dolphin", self.config.read_text())

    def test_login_switches_once(self):
        self.install_loaf()
        self.assertEqual(self.run_tool("login").returncode, 0)
        self.assertEqual(self.mime.read_text().strip(), "loaf.desktop")
        data = json.loads(self.config.read_text())
        self.assertEqual(data["dock"]["pinnedApps"], ["loaf", "kitty"])
        self.assertEqual(data["launcher"]["pinnedApps"], ["loaf", "firefox"])
        # A later choice stays: login doesn't run again.
        self.assertEqual(self.run_tool("use", "org.kde.dolphin").returncode, 0)
        self.run_tool("login")
        self.assertEqual(self.mime.read_text().strip(), "org.kde.dolphin.desktop")

    def test_status(self):
        self.install_loaf()
        out = self.run_tool().stdout
        self.assertIn("Loaf             installed", out)


class DefaultsTest(unittest.TestCase):
    def test_loaf_comes_first(self):
        variables = (ROOT / "dots/.config/hypr/hyprland/variables.lua").read_text()
        self.assertIn("launch_first_available.sh 'loaf' 'dolphin'", variables)
        pkg = (ROOT / "sdata/dist-arch/illogical-impulse-kde/PKGBUILD").read_text()
        self.assertIn("loaf-fm", pkg)
        self.assertIn("halcyon_file_manager.py login", (ROOT / "dots/.config/hypr/hyprland/halcyon/init.lua").read_text())


if __name__ == "__main__":
    unittest.main()
