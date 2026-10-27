"""The themes' own app pickers (modules/ii/themedLauncher): which theme gets which, that Super opens it in place of the
overview, the book's paging, and the phone's four apps. Run: python3 -m unittest discover -s tests"""

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
II = ROOT / "dots/.config/quickshell/ii"
LAUNCHER = II / "modules/ii/themedLauncher"
NODE = shutil.which("node")


def node(script):
    return json.loads(subprocess.run([NODE, "-e", script], capture_output=True, text=True, check=True).stdout)


@unittest.skipUnless(NODE, "node is not installed")
class WhichPickerTest(unittest.TestCase):
    def picker(self, enabled, theme):
        src = (II / "GlobalStates.qml").read_text()
        expr = re.search(r"property string themedLauncher: (.*?)\n    \S", src, re.S).group(1)
        script = (f"const Config = {{ options: {{ halcyon: {{ themedLauncher: {json.dumps(enabled)}, theme: {json.dumps(theme)} }} }} }};\n"
                  f"console.log(JSON.stringify({expr}));")
        return node(script)

    def test_the_three_themes(self):
        self.assertEqual(self.picker(True, "manga-ink"), "book")
        self.assertEqual(self.picker(True, "manga-ink-dark"), "book")
        self.assertEqual(self.picker(True, "after-icey"), "phone")

    def test_other_themes_and_off(self):
        self.assertEqual(self.picker(True, "silence"), "")
        self.assertEqual(self.picker(True, ""), "")
        self.assertEqual(self.picker(False, "manga-ink"), "")
        self.assertEqual(self.picker(False, "after-icey"), "")


@unittest.skipUnless(NODE, "node is not installed")
class BookPagingTest(unittest.TestCase):
    def paging(self, count):
        src = (LAUNCHER / "MangaBook.qml").read_text()
        per = re.search(r"readonly property int perPage: (\d+)", src).group(1)
        pages = re.search(r"readonly property int pageCount: (.*)\n", src).group(1)
        spreads = re.search(r"readonly property int spreads: (.*)\n", src).group(1)
        script = (f"const perPage = {per}; const apps = {{ length: {count} }};\n"
                  f"const pageCount = {pages};\nconst spreads = {spreads};\n"
                  "console.log(JSON.stringify([pageCount, spreads]));")
        return node(script)

    def test_always_a_whole_spread(self):
        self.assertEqual(self.paging(0), [2, 1])
        self.assertEqual(self.paging(16), [2, 1])
        self.assertEqual(self.paging(32), [2, 1])
        self.assertEqual(self.paging(33), [4, 2])
        self.assertEqual(self.paging(43), [4, 2])
        self.assertEqual(self.paging(65), [6, 3])

    def test_turns_stop_at_the_covers(self):
        src = (LAUNCHER / "MangaBook.qml").read_text()
        self.assertIn("if (turning || spread >= spreads - 1)", src)
        self.assertIn("if (turning || spread <= 0)", src)


class WiringTest(unittest.TestCase):
    def test_super_opens_it_in_place_of_the_overview(self):
        overview = (II / "modules/ii/overview/Overview.qml").read_text()
        self.assertIn('GlobalStates.overviewOpen && GlobalStates.themedLauncher === ""', overview)
        family = (II / "panelFamilies/IllogicalImpulseFamily.qml").read_text()
        self.assertIn("import qs.modules.ii.themedLauncher", family)
        self.assertIn("PanelLoader { component: ThemedLauncher {} }", family)
        launcher = (LAUNCHER / "ThemedLauncher.qml").read_text()
        self.assertIn('"MangaBook.qml"', launcher)
        self.assertIn('"IceyPhone.qml"', launcher)

    def test_a_setting_on_by_default(self):
        config = (II / "modules/common/Config.qml").read_text()
        self.assertIn("property bool themedLauncher: true", config)
        settings = (II / "modules/settings/HalcyonConfig.qml").read_text()
        self.assertIn("Config.options.halcyon.themedLauncher = checked", settings)

    def test_the_phone_has_its_four_apps(self):
        phone = (LAUNCHER / "IceyPhone.qml").read_text()
        for page in ("apps", "auto", "theme", "calc"):
            self.assertIn(f'page: "{page}"', phone)
            self.assertIn(f'name: "{page}"', phone)
        # Auto runs whatever LauncherSearch makes of the typing: an app, a sum, a command.
        self.assertIn("host.runResult(LauncherSearch.results[0])", phone)

    def test_both_animate_out_before_they_go(self):
        for name in ("MangaBook.qml", "IceyPhone.qml"):
            src = (LAUNCHER / name).read_text()
            self.assertIn("function close()", src)
            self.assertIn("ScriptAction { script: ", src)
            self.assertIn(".closed()", src)


if __name__ == "__main__":
    unittest.main()
