"""`halcyon browsers`: the Firefox and Chromium themes made from the shell's colours, written into fake profiles
and flags files, and taken out again without touching anything else. Run: python3 -m unittest discover -s tests"""

import importlib.util
import json
import re
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HALCYON = ROOT / "dots/.config/hypr/hyprland/halcyon"
spec = importlib.util.spec_from_file_location("halcyon_browsers", HALCYON / "halcyon_browsers.py")
browsers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(browsers)

RED_SUN = json.loads((HALCYON / "themes/red-sun.json").read_text())["shell"]


class Sandbox:
    """A home folder with a Firefox profile, a LibreWolf profile and Chromium's flags file."""

    def __init__(self, root):
        self.root = Path(root)
        self.ff = self.root / ".mozilla/firefox"
        (self.ff / "abc.default-release/chrome").mkdir(parents=True)
        (self.ff / "profiles.ini").write_text(
            "[General]\nStartWithLastProfile=1\n\n[Profile0]\nName=default-release\nIsRelative=1\n"
            "Path=abc.default-release\nDefault=1\n\n[Install4F96D1932A9F858E]\nDefault=abc.default-release\n")
        self.lw = self.root / ".librewolf"
        (self.lw / "xyz.default").mkdir(parents=True)
        (self.lw / "profiles.ini").write_text("[Profile0]\nName=default\nIsRelative=1\nPath=xyz.default\n")
        self.colors = self.root / "colors.json"
        self.colors.write_text(json.dumps(RED_SUN))
        self.flags = self.root / ".config/chromium-flags.conf"
        self.flags.parent.mkdir(parents=True)
        self.flags.write_text("--ozone-platform-hint=wayland\n")
        self.theme_dir = self.root / ".local/share/halcyon/chromium-theme"
        self.config = self.root / ".config/illogical-impulse/config.json"
        self.config.parent.mkdir(parents=True)
        self.config.write_text("{}")
        self.active = self.root / "active"
        self.patches = [
            unittest.mock.patch.object(browsers, "FIREFOX_ROOTS", [("Firefox", self.ff), ("LibreWolf", self.lw),
                                                                   ("Zen", self.root / ".zen")]),
            unittest.mock.patch.object(browsers, "COLORS", self.colors),
            unittest.mock.patch.object(browsers, "CHROMIUM_FLAGS", [("Chromium", self.flags)]),
            unittest.mock.patch.object(browsers, "CHROMIUM_THEME", self.theme_dir),
            unittest.mock.patch.object(browsers, "SHELL_CONFIG", self.config),
            unittest.mock.patch.object(browsers, "ACTIVE_THEME", self.active),
            unittest.mock.patch.object(browsers, "DATA", self.root / ".local/share"),
            unittest.mock.patch.object(browsers, "chrome_installed", return_value=False),
            unittest.mock.patch.object(browsers.shutil, "which", return_value=None),  # no notify-send in tests
        ]

    def __enter__(self):
        for p in self.patches:
            p.start()
        return self

    def __exit__(self, *exc):
        for p in self.patches:
            p.stop()


class ColoursTest(unittest.TestCase):
    def test_missing_or_bad_values_fall_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "colors.json")
            path.write_text(json.dumps({"primary": "#ff8a7a", "surface": "not a colour"}))
            colors = browsers.load_colors(path)
        self.assertEqual(colors["primary"], "#FF8A7A")
        self.assertEqual(colors["surface"], browsers.FALLBACK["surface"])
        self.assertEqual(browsers.load_colors(Path("/nonexistent"))["on_surface"], browsers.FALLBACK["on_surface"])

    def test_mix_and_rgb(self):
        self.assertEqual(browsers.mix("#000000", "#FFFFFF", 0.5), "#808080")
        self.assertEqual(browsers.rgb("#FF4940"), [255, 73, 64])


class FirefoxTest(unittest.TestCase):
    def test_finds_profiles_of_every_firefox(self):
        with tempfile.TemporaryDirectory() as tmp, Sandbox(tmp) as box:
            found = browsers.firefox_profiles()
        self.assertEqual([(b, p.name) for b, p in found], [("Firefox", "abc.default-release"), ("LibreWolf", "xyz.default")])

    def test_install_keeps_the_users_own_css_and_prefs(self):
        with tempfile.TemporaryDirectory() as tmp, Sandbox(tmp) as box:
            profile = box.ff / "abc.default-release"
            (profile / "chrome/userChrome.css").write_text("@charset \"UTF-8\";\n#sidebar { width: 300px; }\n")
            (profile / "user.js").write_text('user_pref("browser.startup.page", 3);\n')
            colors = browsers.load_colors()
            self.assertTrue(browsers.install_firefox(profile, colors, "red-sun"))
            self.assertFalse(browsers.install_firefox(profile, colors, "red-sun"))  # nothing new: no restart asked
            chrome_css = (profile / "chrome/userChrome.css").read_text()
            lines = chrome_css.splitlines()
            self.assertTrue(lines[0].startswith("@charset"))
            self.assertIn('@import url("halcyon.css")', lines[1])
            self.assertEqual(chrome_css.count("halcyon.css"), 1)
            self.assertIn("#sidebar { width: 300px; }", chrome_css)
            user_js = (profile / "user.js").read_text()
            self.assertIn('"browser.startup.page", 3', user_js)
            self.assertEqual(user_js.count("legacyUserProfileCustomizations"), 1)
            theme = (profile / "chrome/halcyon.css").read_text()
            self.assertIn(f"--toolbar-field-focus-border-color: {RED_SUN['primary'].upper()}", theme)
            self.assertIn("box-shadow: 0 0 14px", theme)  # Red Sun's ember on the selected tab
            self.assertIn('@import url("halcyon-content.css")', (profile / "chrome/userContent.css").read_text())

            browsers.remove_firefox(profile)
            self.assertEqual((profile / "chrome/userChrome.css").read_text(),
                             "@charset \"UTF-8\";\n#sidebar { width: 300px; }\n")
            self.assertFalse((profile / "chrome/halcyon.css").exists())
            self.assertFalse((profile / "chrome/userContent.css").exists())  # it was only ours
            self.assertEqual((profile / "user.js").read_text(), 'user_pref("browser.startup.page", 3);\n')

    def test_firefox_uses_its_dark_base_under_a_dark_palette(self):
        dark = browsers.user_js(browsers.load_colors(Path("/nonexistent")))
        self.assertIn('user_pref("ui.systemUsesDarkTheme", 1);', dark)
        self.assertIn('user_pref("browser.theme.toolbar-theme", 0);', dark)
        light = browsers.user_js({**browsers.FALLBACK, "surface": "#FFF8F6"})
        self.assertIn('user_pref("ui.systemUsesDarkTheme", 0);', light)
        self.assertIn('user_pref("browser.theme.content-theme", 1);', light)

    def test_flatpak_profiles_are_looked_for(self):
        roots = [str(root) for _name, root in browsers.FIREFOX_ROOTS]
        self.assertTrue(any("org.mozilla.firefox" in r for r in roots))
        self.assertTrue(any(r.endswith("config/mozilla/firefox") for r in roots))

    def test_css_is_balanced_and_every_value_is_filled(self):
        css = browsers.firefox_css(browsers.load_colors(Path("/nonexistent")), "red-sun")
        css += browsers.firefox_content_css(browsers.load_colors(Path("/nonexistent")))
        body = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        self.assertEqual(body.count("{"), body.count("}"))
        self.assertNotIn("{c[", css)
        self.assertNotRegex(css, r":\s*!important")  # no empty values


class ChromiumTest(unittest.TestCase):
    def test_manifest_is_a_valid_theme(self):
        manifest = browsers.chromium_manifest(browsers.load_colors(Path("/nonexistent")), "2026.1014.1530.5", True,
                                              "red-sun")
        self.assertEqual(manifest["manifest_version"], 3)
        self.assertRegex(manifest["version"], r"^\d+(\.\d+){0,3}$")
        for part in manifest["version"].split("."):
            self.assertLessEqual(int(part), 65535)
        for name, value in manifest["theme"]["colors"].items():
            self.assertIn(len(value), (3, 4), name)
            self.assertTrue(all(0 <= v <= 255 for v in value[:3]), name)
        self.assertEqual(manifest["theme"]["images"], {"theme_ntp_background": "images/ntp.png"})
        self.assertIn("Red Sun", manifest["name"])

    def test_version_always_fits(self):
        for t in (0, 1_760_000_000, 4_102_444_799):
            for part in browsers.version_now(t).split("."):
                self.assertLessEqual(int(part), 65535)

    def test_flags_merge_with_an_existing_load_extension(self):
        folder = Path("/home/u/.local/share/halcyon/chromium-theme")
        text = "--ozone-platform-hint=wayland\n--load-extension=/opt/ext1\n"
        added = browsers.add_load_extension(text, folder)
        self.assertIn(f"--load-extension=/opt/ext1,{folder}", added)
        self.assertEqual(browsers.add_load_extension(added, folder), added)
        self.assertEqual(browsers.remove_load_extension(added, folder), text)
        alone = browsers.add_load_extension("", folder)
        self.assertEqual(alone, f"--load-extension={folder}\n")
        self.assertEqual(browsers.remove_load_extension(alone, folder), "")

    def test_update_writes_the_theme_and_only_bumps_it_on_change(self):
        with tempfile.TemporaryDirectory() as tmp, Sandbox(tmp) as box:
            box.active.write_text("red-sun\n")
            first = browsers.update(quiet=True)
            manifest = json.loads((box.theme_dir / "manifest.json").read_text())
            self.assertIn(f"--load-extension={box.theme_dir}", box.flags.read_text())
            self.assertIn("--ozone-platform-hint=wayland", box.flags.read_text())
            self.assertEqual(sorted(first["restart"]), ["Chromium", "Firefox", "LibreWolf"])
            self.assertEqual(sorted(p.name for p in box.theme_dir.iterdir()), ["manifest.json"])

            second = browsers.update(quiet=True)
            self.assertEqual(second["restart"], [])
            self.assertEqual(json.loads((box.theme_dir / "manifest.json").read_text())["version"], manifest["version"])

            colors = json.loads(box.colors.read_text())
            colors["primary"] = "#00FF00"
            box.colors.write_text(json.dumps(colors))
            third = browsers.update(quiet=True)
            self.assertIn("Chromium", third["restart"])
            self.assertEqual(json.loads((box.theme_dir / "manifest.json").read_text())["theme"]["colors"]["ntp_link"],
                             [0, 255, 0])

    def test_settings_turn_each_browser_off(self):
        with tempfile.TemporaryDirectory() as tmp, Sandbox(tmp) as box:
            box.config.write_text(json.dumps({"halcyon": {"browsers": {"firefox": False}}}))
            report = browsers.update(quiet=True)
            self.assertEqual(report["firefox"], [])
            self.assertFalse((box.ff / "abc.default-release/chrome/halcyon.css").exists())
            self.assertTrue((box.theme_dir / "manifest.json").exists())

    def test_off_removes_everything_it_added(self):
        with tempfile.TemporaryDirectory() as tmp, Sandbox(tmp) as box:
            browsers.update(quiet=True)
            browsers.off()
            self.assertEqual(box.flags.read_text(), "--ozone-platform-hint=wayland\n")
            self.assertFalse(box.theme_dir.exists())
            self.assertFalse((box.ff / "abc.default-release/chrome/halcyon.css").exists())
            self.assertFalse((box.ff / "abc.default-release/user.js").exists())


class HooksTest(unittest.TestCase):
    def test_wallpaper_changes_update_the_browsers_but_theme_applies_do_it_themselves(self):
        applycolor = (ROOT / "dots/.config/quickshell/ii/scripts/colors/applycolor.sh").read_text()
        self.assertIn('if [ -z "$HALCYON_THEME_APPLYING" ]', applycolor)
        self.assertIn("halcyon_browsers.py\" update --quiet", applycolor)
        theme = (HALCYON / "halcyon-theme").read_text()
        for function in ("def cmd_apply", "def cmd_off", "def cmd_detach"):
            body = theme[theme.index(function):]
            body = body[:body.index("\ndef ", 1)]
            self.assertIn("update_browsers()", body, function)


if __name__ == "__main__":
    unittest.main()
