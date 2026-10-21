"""Theme switch rules (halcyon-theme rules): what changes when the theme switches to, or away from, a theme.
Run against a temporary home with a stand-in gsettings. Run: python3 -m unittest discover -s tests"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "dots/.config/hypr/hyprland/halcyon/halcyon-theme"
SETTINGS = ROOT / "dots/.config/quickshell/ii/modules/settings/HalcyonConfig.qml"
CONFIG_QML = ROOT / "dots/.config/quickshell/ii/modules/common/Config.qml"

GSETTINGS = """#!/bin/sh
state="$HOME/gsettings-icon"
if [ "$1" = get ]; then echo "'$(cat "$state" 2>/dev/null || echo Adwaita)'"; fi
if [ "$1" = set ]; then echo "$4" > "$state"; fi
"""


class SwitchRulesTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name)
        self.bin = self.home / "bin"
        self.bin.mkdir()
        (self.bin / "gsettings").write_text(GSETTINGS)
        (self.bin / "gsettings").chmod(0o755)
        self.cfg = self.home / ".config/illogical-impulse/config.json"
        self.cfg.parent.mkdir(parents=True)

    def write_rules(self, rules, **extra):
        self.cfg.write_text(json.dumps({"halcyon": {"switchRules": rules}, **extra}))

    def config(self):
        return json.loads(self.cfg.read_text())

    def run_tool(self, *args):
        env = {"PATH": f"{self.bin}:/usr/bin:/bin", "HOME": str(self.home), "XDG_CONFIG_HOME": str(self.home / ".config"),
               "XDG_STATE_HOME": str(self.home / "state"), "XDG_DATA_HOME": str(self.home / "data")}
        done = subprocess.run([sys.executable, str(TOOL), *args], env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout

    def test_a_widget_turned_off_for_a_theme_comes_back_after_it(self):
        self.write_rules([{"theme": "after-icey", "when": "to", "action": "widget", "target": "revolver",
                           "value": "off", "restore": True}])
        self.run_tool("rules", "run", "to", "after-icey")
        self.assertIs(self.config()["background"]["widgets"]["revolver"]["enable"], False)
        self.run_tool("rules", "run", "from", "after-icey")
        self.assertIs(self.config()["background"]["widgets"]["revolver"]["enable"], True,
                      "the revolver is on by default, so that is what comes back")
        self.assertFalse((self.home / "state/halcyon/switch-rules-restore.json").exists())

    def test_from_rules_and_any_theme(self):
        self.write_rules([{"theme": "red-sun", "when": "from", "action": "effects", "value": "light"},
                          {"theme": "*", "when": "to", "action": "setting", "target": "bar.vertical", "value": "true"},
                          {"theme": "hsr", "when": "to", "action": "widget", "target": "lyrics", "value": "on"}])
        self.run_tool("rules", "run", "from", "red-sun")
        self.assertEqual(self.config()["halcyon"]["effects"], "light")
        self.run_tool("rules", "run", "to", "manga-ink")
        self.assertIs(self.config()["bar"]["vertical"], True, "a JSON value is read as JSON")
        self.assertNotIn("widgets", self.config().get("background", {}), "another theme's rule doesn't run")

    def test_icon_theme_rule_sets_gtk_and_qt_and_puts_it_back(self):
        self.write_rules([{"theme": "after-icey", "when": "to", "action": "icons", "value": "Papirus-Dark",
                           "restore": True}])
        self.run_tool("rules", "run", "to", "after-icey")
        self.assertEqual((self.home / "gsettings-icon").read_text().strip(), "Papirus-Dark")
        self.assertIn("[Icons]\nTheme=Papirus-Dark", (self.home / ".config/kdeglobals").read_text())
        self.run_tool("rules", "run", "from", "after-icey")
        self.assertEqual((self.home / "gsettings-icon").read_text().strip(), "Adwaita")

    def test_icon_themes_are_listed_without_cursor_themes(self):
        icons = self.home / "data/icons"
        (icons / "Papirus").mkdir(parents=True)
        (icons / "Papirus/index.theme").write_text("[Icon Theme]\nName=Papirus\nDirectories=16x16/apps\n")
        (icons / "Bibata").mkdir()
        (icons / "Bibata/index.theme").write_text("[Icon Theme]\nName=Bibata\nInherits=hicolor\n")
        listing = json.loads(self.run_tool("rules", "icons", "--json"))
        self.assertIn({"id": "Papirus", "name": "Papirus"}, listing["themes"])
        self.assertNotIn("Bibata", [t["id"] for t in listing["themes"]])
        self.assertEqual(listing["current"], "Adwaita")

    def test_listing(self):
        rules = [{"theme": "hsr", "when": "to", "action": "widget", "target": "clock", "value": "off"}]
        self.write_rules(rules)
        self.assertEqual(json.loads(self.run_tool("rules", "--json")), rules)
        self.assertIn("hsr", self.run_tool("rules"))

    def test_applying_and_turning_off_a_theme_run_them(self):
        source = TOOL.read_text()
        apply = source[source.index("def cmd_apply"):source.index("def update_browsers")]
        self.assertIn('run_switch_rules("from", previous)', apply)
        self.assertLess(apply.index('run_switch_rules("to", theme_id)'), apply.index("write_window_style"),
                        "an effects rule takes effect with the theme")
        off = source[source.index("def cmd_off"):source.index("def cmd_menu")]
        self.assertIn('run_switch_rules("to", "off")', off)

    def test_settings_make_them(self):
        self.assertIn("property list<var> switchRules", CONFIG_QML.read_text())
        settings = SETTINGS.read_text()
        self.assertIn("Config.options.halcyon.switchRules", settings)
        self.assertIn('"rules", "icons", "--json"', settings)


if __name__ == "__main__":
    unittest.main()
