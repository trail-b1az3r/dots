"""The theme picker and the theme while away: `halcyon-theme list --json` and `previews`, which the picker shows,
`menu` opening the shell's picker before fuzzel, and IdleTheme.qml's choice of the next theme (run under node).
Run: python3 -m unittest discover -s tests"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "dots/.config/hypr/hyprland/halcyon/halcyon-theme"
II = ROOT / "dots/.config/quickshell/ii"
NODE = shutil.which("node")


class PickerDataTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        home = Path(self.tmp.name)
        self.bin = home / "bin"
        self.bin.mkdir()
        self.env = {**os.environ, "HOME": str(home), "XDG_CONFIG_HOME": str(home / "c"),
                    "XDG_DATA_HOME": str(home / "d"), "XDG_STATE_HOME": str(home / "s"),
                    "XDG_CACHE_HOME": str(home / "cache"), "PATH": f"{self.bin}:{os.environ['PATH']}"}

    def run_tool(self, *args):
        return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True, env=self.env,
                              timeout=120)

    def test_list_json_has_what_a_card_shows(self):
        done = self.run_tool("list", "--json")
        self.assertEqual(done.returncode, 0, done.stderr)
        data = json.loads(done.stdout)
        ids = [t["id"] for t in data["themes"]]
        for theme_id in ("silence", "manga-ink-dark", "after-icey", "red-sun"):
            self.assertIn(theme_id, ids)
        silence = next(t for t in data["themes"] if t["id"] == "silence")
        self.assertEqual(set(silence["colors"]), {"background", "on_background", "surface_container", "primary",
                                                  "secondary", "tertiary"})
        self.assertEqual(silence["preview"], "", "no preview before one is made")
        self.assertFalse(silence["active"])

    @unittest.skipUnless(shutil.which("ffmpeg"), "no ffmpeg")
    def test_previews_are_made_from_the_wallpapers_that_are_there(self):
        done = self.run_tool("previews")
        self.assertEqual(done.returncode, 0, done.stderr)
        previews = Path(self.env["XDG_CACHE_HOME"]) / "halcyon/theme-previews"
        made = sorted(p.stem for p in previews.glob("*.jpg"))
        self.assertIn("red-sun", made, "a shipped wallpaper")
        self.assertNotIn("silence", made, "Silence's wallpaper isn't fetched here")
        listed = json.loads(self.run_tool("list", "--json").stdout)
        red_sun = next(t for t in listed["themes"] if t["id"] == "red-sun")
        self.assertTrue(red_sun["preview"].endswith("red-sun.jpg"))

    def test_menu_opens_the_shells_picker_first(self):
        calls = Path(self.tmp.name) / "calls"
        qs = self.bin / "qs"
        qs.write_text(f"#!/bin/sh\necho \"$@\" >> '{calls}'\n")
        qs.chmod(0o755)
        done = self.run_tool("menu")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(calls.read_text().strip(), "-c ii ipc call themePicker toggle")


@unittest.skipUnless(NODE, "node is not installed")
class IdlePickTest(unittest.TestCase):
    def pick(self, *args):
        source = (II / "modules/ii/idleTheme/IdleTheme.qml").read_text()
        body = re.search(r"(function pick\(mode, current, ids, chosen\) \{.*?\n    \})", source, re.S).group(1)
        script = body + f"\nconsole.log(JSON.stringify(pick(...{json.dumps(list(args))})))"
        return json.loads(subprocess.run([NODE, "-e", script], capture_output=True, text=True, check=True).stdout)

    def test_next_goes_round(self):
        ids = ["a", "b", "c"]
        self.assertEqual(self.pick("next", "a", ids, ""), "b")
        self.assertEqual(self.pick("next", "c", ids, ""), "a")
        self.assertEqual(self.pick("next", "", ids, ""), "a", "no theme yet: the first")

    def test_random_is_never_the_same(self):
        for _ in range(10):
            self.assertIn(self.pick("random", "b", ["a", "b", "c"], ""), ("a", "c"))

    def test_one_theme(self):
        self.assertEqual(self.pick("one", "a", ["a", "b"], "silence"), "silence")
        self.assertEqual(self.pick("one", "silence", ["a", "b"], "silence"), "", "already in it")


class WiringTest(unittest.TestCase):
    def test_loaded_by_the_shell(self):
        family = (II / "panelFamilies/IllogicalImpulseFamily.qml").read_text()
        self.assertIn("component: ThemePicker {}", family)
        self.assertIn("component: IdleTheme {}", family)


if __name__ == "__main__":
    unittest.main()
