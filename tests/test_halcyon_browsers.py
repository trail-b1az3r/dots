"""`halcyon browsers`: the Firefox and Chromium themes made from the shell's colours, written into fake profiles
and flags files, and taken out again without touching anything else. Run: python3 -m unittest discover -s tests"""

import importlib.util
import json
import os
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

    def test_finds_a_profile_profiles_ini_does_not_list(self):
        # Firefox's newer profile manager keeps its own list; a used profile has prefs.js.
        with tempfile.TemporaryDirectory() as tmp, Sandbox(tmp) as box:
            extra = box.ff / "Profiles/qrs.work"
            extra.mkdir(parents=True)
            (extra / "prefs.js").write_text("// prefs\n")
            (box.ff / "unused-folder").mkdir()
            found = browsers.firefox_profiles()
        self.assertIn(("Firefox", "qrs.work"), [(b, p.name) for b, p in found])
        self.assertNotIn("unused-folder", [p.name for _b, p in found])

    def test_says_when_firefox_needs_a_restart_to_show_it(self):
        with tempfile.TemporaryDirectory() as tmp, Sandbox(tmp) as box:
            profile = box.ff / "abc.default-release"
            browsers.install_firefox(profile, browsers.load_colors())
            os.symlink("127.0.0.1:+1234", profile / "lock")       # Firefox's own lock, made when it starts
            os.utime(profile / "lock", (1000, 1000), follow_symlinks=False)
            self.assertTrue(browsers.running_since_before(profile))
            os.utime(profile / "lock", None, follow_symlinks=False)
            os.utime(profile / "chrome/halcyon.css", (1000, 1000))
            self.assertFalse(browsers.running_since_before(profile))
            os.unlink(profile / "lock")
            self.assertFalse(browsers.running_since_before(profile), "not running")

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
            self.assertIn("0 0 16px rgba(255, 138, 122, 0.22)", theme)  # Red Sun's ember glow on the selected tab
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


class SitesTest(unittest.TestCase):
    """How far the Firefox theme reaches into web pages: off, accents (the default) or override."""

    def test_the_default_is_accents_and_a_bad_value_falls_back_to_it(self):
        with tempfile.TemporaryDirectory() as tmp, Sandbox(tmp) as box:
            self.assertEqual(browsers.sites_level(), "accents")
            for stored, expected in (("off", "off"), ("override", "override"), ("accents", "accents"),
                                     ("everything", "accents"), (7, "accents"), (None, "accents")):
                box.config.write_text(json.dumps({"halcyon": {"browsers": {"sites": stored}}}))
                self.assertEqual(browsers.sites_level(), expected, stored)

    def test_accents_colour_what_a_page_leaves_to_the_browser_and_nothing_more(self):
        colors = browsers.load_colors(Path("/nonexistent"))
        block = browsers.sites_css(colors, "accents")
        self.assertIn(f"accent-color: {colors['primary']}", block)
        self.assertIn(f"caret-color: {colors['primary']}", block)
        self.assertIn("scrollbar-color: rgba(", block)
        self.assertIn(":focus-visible", block)
        self.assertNotIn("!important", block, "user styles without !important: a site that styles it itself wins")
        self.assertNotIn("background:", block.replace("background-color", ""), "no page background is painted")
        body = re.sub(r"/\*.*?\*/", "", block, flags=re.S)
        self.assertEqual(body.count("{"), body.count("}"))
        self.assertEqual(browsers.sites_css(colors, "off"), "")
        self.assertEqual(browsers.sites_css(colors, "override"), block)

    def test_the_content_css_carries_the_block_unless_it_is_off(self):
        colors = browsers.load_colors(Path("/nonexistent"))
        self.assertIn("Every site:", browsers.firefox_content_css(colors))
        self.assertIn("Every site:", browsers.firefox_content_css(colors, sites="override"))
        self.assertNotIn("Every site:", browsers.firefox_content_css(colors, sites="off"))
        # The new tab and Firefox's own pages are styled either way.
        self.assertIn('url("about:newtab")', browsers.firefox_content_css(colors, sites="off"))

    def test_only_override_forces_page_colours(self):
        colors = browsers.load_colors(Path("/nonexistent"))
        for level in ("off", "accents"):
            self.assertNotIn("document_color_use", browsers.user_js(colors, level))
        forced = browsers.user_js(colors, "override")
        self.assertIn('user_pref("browser.display.document_color_use", 2);', forced)
        self.assertIn(f'user_pref("browser.display.background_color", "{colors["surface"]}");', forced)
        self.assertIn(f'user_pref("browser.display.foreground_color", "{colors["on_surface"]}");', forced)
        self.assertIn(f'user_pref("browser.anchor_color", "{colors["primary"]}");', forced)
        self.assertRegex(forced, r'user_pref\("browser.visited_color", "#[0-9A-F]{6}"\);')

    def test_leaving_override_says_so_out_loud_because_firefox_keeps_the_pref(self):
        with tempfile.TemporaryDirectory() as tmp, Sandbox(tmp) as box:
            profile = box.ff / "abc.default-release"
            colors = browsers.load_colors()
            browsers.install_firefox(profile, colors, "red-sun", "override")
            self.assertIn('"browser.display.document_color_use", 2', (profile / "user.js").read_text())
            browsers.install_firefox(profile, colors, "red-sun", "accents")
            text = (profile / "user.js").read_text()
            self.assertIn('"browser.display.document_color_use", 0', text)
            self.assertNotIn('"browser.display.document_color_use", 2', text)
            self.assertNotIn("browser.display.background_color", text)
            # It stays: a second update before Firefox has restarted must not undo it, and it asks for no restart.
            self.assertFalse(browsers.install_firefox(profile, colors, "red-sun", "accents"))
            self.assertEqual(text, (profile / "user.js").read_text())
            # Back to override: the restore line goes, the override comes back.
            browsers.install_firefox(profile, colors, "red-sun", "override")
            self.assertNotIn('"browser.display.document_color_use", 0', (profile / "user.js").read_text())
            self.assertIn('"browser.display.document_color_use", 2', (profile / "user.js").read_text())

    def test_a_profile_that_never_overrode_gets_no_restore_line(self):
        with tempfile.TemporaryDirectory() as tmp, Sandbox(tmp) as box:
            profile = box.ff / "abc.default-release"
            browsers.install_firefox(profile, browsers.load_colors(), "red-sun", "accents")
            self.assertNotIn("document_color_use", (profile / "user.js").read_text())

    def test_taking_the_theme_away_while_overriding_gives_sites_their_colours_back(self):
        with tempfile.TemporaryDirectory() as tmp, Sandbox(tmp) as box:
            profile = box.ff / "abc.default-release"
            (profile / "user.js").write_text('user_pref("browser.startup.page", 3);\n')
            browsers.install_firefox(profile, browsers.load_colors(), "red-sun", "override")
            browsers.remove_firefox(profile)
            text = (profile / "user.js").read_text()
            self.assertIn('"browser.startup.page", 3', text, "the user's own prefs stay")
            self.assertIn('"browser.display.document_color_use", 0', text)
            self.assertNotIn('"browser.display.document_color_use", 2', text)
            self.assertNotIn("legacyUserProfileCustomizations", text)

    def test_the_command_sets_the_level_and_writes_the_profiles(self):
        with tempfile.TemporaryDirectory() as tmp, Sandbox(tmp) as box:
            box.config.write_text(json.dumps({"bar": {"vertical": True}}))
            self.assertEqual(browsers.main(["sites", "override", "--quiet"]), 0)
            stored = json.loads(box.config.read_text())
            self.assertEqual(stored["halcyon"]["browsers"]["sites"], "override")
            self.assertEqual(stored["bar"], {"vertical": True}, "the rest of the config is kept")
            for profile in (box.ff / "abc.default-release", box.lw / "xyz.default"):
                self.assertIn("document_color_use", (profile / "user.js").read_text())
                self.assertIn("Every site:", (profile / "chrome/halcyon-content.css").read_text())
            self.assertEqual(browsers.main(["sites", "off", "--quiet"]), 0)
            profile = box.ff / "abc.default-release"
            self.assertNotIn("Every site:", (profile / "chrome/halcyon-content.css").read_text())
            self.assertIn('"browser.display.document_color_use", 0', (profile / "user.js").read_text())

    def test_the_command_refuses_an_unknown_level_and_an_unreadable_config(self):
        with tempfile.TemporaryDirectory() as tmp, Sandbox(tmp) as box:
            with self.assertRaises(SystemExit):
                browsers.main(["sites", "everything"])
            box.config.write_text("{ not json")
            self.assertEqual(browsers.main(["sites", "override", "--quiet"]), 1)
            self.assertEqual(box.config.read_text(), "{ not json")

    def test_status_reports_the_level(self):
        with tempfile.TemporaryDirectory() as tmp, Sandbox(tmp):
            self.assertEqual(browsers.status()["sites"], "accents")


class ChromiumTest(unittest.TestCase):
    def test_new_tab_image_fills_the_screen(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("no Pillow")
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp, "wall.jpg")
            Image.new("RGB", (2560, 1440), (200, 40, 60)).save(src)
            out = Path(tmp, "ntp.png")
            # A 3:2 screen (a Surface): cropped from the middle to its shape, at its full size.
            self.assertTrue(browsers.ntp_image(src, out, size=(2736, 1824)))
            with Image.open(out) as img:
                self.assertEqual(img.size, (2736, 1824))
            self.assertFalse(browsers.ntp_image(None, out))

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
