"""The Settings search: its index is read from the Settings pages themselves (SettingsIndex.js), so every setting is
found without a list to keep in step. Run: python3 -m unittest discover -s tests"""

import json
import shutil
import subprocess
import unittest
from pathlib import Path

II = Path(__file__).resolve().parent.parent / "dots/.config/quickshell/ii"
INDEX = II / "modules/settings/SettingsIndex.js"
SETTINGS = (II / "settings.qml").read_text()

RUNNER = r"""
const fs = require("fs");
eval(fs.readFileSync(process.argv[1], "utf8").replace(".pragma library", "") + "; globalThis.parse = parse; globalThis.score = score;");
const pages = process.argv.slice(2);
let all = [];
pages.forEach((f, i) => { all = all.concat(parse(fs.readFileSync(f, "utf8"), i)); });
const view = e => ({ label: e.label, hint: e.hint, section: e.section, subsection: e.subsection, page: "" });
const find = q => all.map(e => [score(e, view(e), q), e]).filter(x => x[0] > 0).sort((a, b) => b[0] - a[0]).map(x => x[1]);
console.log(JSON.stringify({
  count: all.length,
  wall: find("wall").slice(0, 2),
  bulge: find("monitor bulge")[0],
  resistance: all.find(e => e.label.startsWith("Window resistance")),
  nothing: find("zzzz-no-such-setting").length,
}));
"""


@unittest.skipUnless(shutil.which("node"), "needs node")
class SettingsIndexTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pages = sorted(str(p) for p in (II / "modules/settings").glob("*Config.qml"))
        out = subprocess.run(["node", "-e", RUNNER, str(INDEX), *pages], capture_output=True, text=True, check=True)
        cls.r = json.loads(out.stdout)

    def test_every_page_is_indexed(self):
        self.assertGreater(self.r["count"], 250)

    def test_whole_words_rank_first(self):
        self.assertEqual(self.r["wall"][0]["label"], "The wall between monitors (px)")

    def test_a_setting_knows_where_it_is(self):
        b = self.r["bulge"]
        self.assertEqual(b["label"], "Show the wall bulge on the other monitor")
        self.assertEqual((b["kind"], b["section"], b["icon"]), ("ConfigSwitch", "Plus Tiles", "waves"))

    def test_tooltips_are_searched(self):
        self.assertIn("floating window you drag", self.r["resistance"]["hint"])

    def test_no_match_finds_nothing(self):
        self.assertEqual(self.r["nothing"], 0)


class SettingsWindowTest(unittest.TestCase):
    def test_the_window_has_the_search(self):
        self.assertIn('import "modules/settings/SettingsIndex.js" as SettingsIndex', SETTINGS)
        self.assertIn('placeholderText: Translation.tr("Search settings")', SETTINGS)
        self.assertIn("event.key === Qt.Key_F", SETTINGS)  # Ctrl+F
        self.assertIn('target: "settings"', SETTINGS)
        self.assertIn("function reveal(text: string)", SETTINGS)


if __name__ == "__main__":
    unittest.main()
