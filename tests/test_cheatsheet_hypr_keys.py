"""The cheat sheet's Hypr keys page: which binds are hypr keys (HyprlandKeybinds.qml, run under node), and that the
page is a tab of its own. Run: python3 -m unittest discover -s tests"""

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
II = ROOT / "dots/.config/quickshell/ii"
NODE = shutil.which("node")

S, C, A, SH, MOD3 = 64, 4, 8, 1, 32


def pages(binds):
    src = (II / "services/HyprlandKeybinds.qml").read_text()
    funcs = "\n".join(re.findall(r"(    function (?:isHyperChord|isHyprKey|onPage)\(.*?\n    \})", src, re.S))
    script = ("const root = { hyperMask: 77, mod3Mask: 32 };\n" + funcs.replace("root.isHyperChord", "isHyperChord")
              .replace("root.isHyprKey", "isHyprKey").replace("root.hyperMask", "root.hyperMask")
              + f"\nconst binds = {json.dumps(binds)};\n"
              "console.log(JSON.stringify(binds.map(b => [onPage(b, true), onPage(b, false)])));")
    return json.loads(subprocess.run([NODE, "-e", script], capture_output=True, text=True, check=True).stdout)


@unittest.skipUnless(NODE, "node is not installed")
class HyprKeysTest(unittest.TestCase):
    def test_which_page(self):
        binds = [
            {"modmask": S, "key": "Return", "description": "App: Terminal", "submap": ""},
            {"modmask": S | C | A | SH, "key": "Tab", "description": "Window: Next floating (Hyper + Ctrl + Tab)", "submap": ""},
            {"modmask": MOD3 | C, "key": "Tab", "description": "Window: Next", "submap": ""},
            {"modmask": 0, "key": "H", "description": "Hypr mode: Focus left", "submap": "hypr"},
            {"modmask": S | C, "key": "H", "description": "Shell: Toggle hypr mode", "submap": ""},
        ]
        self.assertEqual(pages(binds), [
            [False, True],   # an ordinary bind: Keybinds only
            [True, False],   # a Hyper chord: Hypr keys only
            [True, False],   # Mod3 counts as Hyper
            [True, False],   # hypr mode's own keys
            [True, True],    # the hypr mode toggle: on both
        ])


class WiringTest(unittest.TestCase):
    def test_a_tab_of_its_own(self):
        sheet = (II / "modules/ii/cheatsheet/Cheatsheet.qml").read_text()
        self.assertIn('"name": Translation.tr("Hypr keys")', sheet)
        self.assertIn("CheatsheetHyprKeys {}", sheet)
        self.assertIn("categoriesOf(false)", (II / "modules/ii/cheatsheet/CheatsheetKeybinds.qml").read_text())


if __name__ == "__main__":
    unittest.main()
