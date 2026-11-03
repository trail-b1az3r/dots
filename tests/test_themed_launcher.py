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
        self.assertEqual(self.picker(True, "sword-art-online"), "sao")

    def test_other_themes_and_off(self):
        self.assertEqual(self.picker(True, "silence"), "")
        self.assertEqual(self.picker(True, ""), "")
        self.assertEqual(self.picker(False, "manga-ink"), "")
        self.assertEqual(self.picker(False, "after-icey"), "")


@unittest.skipUnless(NODE, "node is not installed")
class BookPagingTest(unittest.TestCase):
    """The book's pages, worked out by its own code (the chapters and the layout, lifted from MangaBook.qml)."""

    def layout(self, apps, query=""):
        src = (LAUNCHER / "MangaBook.qml").read_text()
        per = re.search(r"readonly property int perPage: (\d+)", src).group(1)
        chapters = re.search(r"readonly property var chapterDefs: (\[.*?\n    \])", src, re.S).group(1)
        chapter_of = re.search(r"(function chapterOf\(entry\) \{.*?\n    \})", src, re.S).group(1)
        layout = re.search(r"readonly property var layout: (\{.*?\n    \})\n", src, re.S).group(1)
        script = ("const Translation = { tr: s => s };\n"
                  f"const perPage = {per}; const query = {json.dumps(query)}; const apps = {json.dumps(apps)};\n"
                  f"const chapterDefs = {chapters};\n{chapter_of}\n"
                  f"const layout = (() => {layout})();\n"
                  "console.log(JSON.stringify({ kinds: layout.pages.map(p => p.kind), "
                  "chapters: layout.pages.map(p => p.chapter ?? null), toc: layout.toc }));")
        return node(script)

    @staticmethod
    def apps(n, category):
        return [{"name": f"{category}{i}", "categories": [category]} for i in range(n)]

    def test_contents_first_then_a_chapter_per_type(self):
        out = self.layout(self.apps(3, "Game") + self.apps(2, "Office"))
        self.assertEqual(out["kinds"], ["toc", "apps", "apps", "blank"])
        self.assertEqual(out["chapters"][1:3], ["Games", "Work"])
        self.assertEqual([(t["name"], t["number"], t["page"], t["count"]) for t in out["toc"]],
                         [("Games", 1, 1, 3), ("Work", 2, 2, 2)])

    def test_a_long_chapter_runs_on_and_spreads_are_whole(self):
        out = self.layout(self.apps(20, "Development"))
        self.assertEqual(out["kinds"], ["toc", "apps", "apps", "blank"])
        self.assertEqual(len(out["kinds"]) % 2, 0)

    def test_searching_shows_only_the_matches(self):
        out = self.layout(self.apps(3, "Game"), query="ga")
        self.assertEqual(out["kinds"], ["apps", "blank"])
        self.assertEqual(out["toc"], [])

    def test_an_app_without_categories_is_in_everything_else(self):
        out = self.layout([{"name": "odd"}])
        self.assertEqual(out["toc"][0]["name"], "Everything Else")

    def test_turns_stop_at_the_covers(self):
        src = (LAUNCHER / "MangaBook.qml").read_text()
        self.assertIn("if (turning || target === spread || target < 0 || target >= spreads)", src)
        self.assertIn("readonly property int pageCount: Math.max(2, pages.length)", src)


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
        self.assertIn('"SaoMenu.qml"', launcher)

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

    def test_the_sao_menu_has_the_games_buttons_and_asks_before_logging_out(self):
        sao = (LAUNCHER / "SaoMenu.qml").read_text()
        for button in ("status", "items", "party", "map", "messages", "system"):
            self.assertIn(f'id: "{button}"', sao)
        self.assertIn("run: () => menu.confirmLogout = true", sao)
        self.assertIn("Session.logout()", sao)

    def test_all_animate_out_before_they_go(self):
        for name in ("MangaBook.qml", "IceyPhone.qml", "SaoMenu.qml"):
            src = (LAUNCHER / name).read_text()
            self.assertIn("function close()", src)
            self.assertIn("ScriptAction { script: ", src)
            self.assertIn(".closed()", src)


if __name__ == "__main__":
    unittest.main()
