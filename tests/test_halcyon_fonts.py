"""`halcyon fonts`: fonts and zips of them installed for the user, never outside their folder; RightFont from Halcyon's
copy, or from its site with --latest. Run: python3 -m unittest discover -s tests"""

import io
import os
import sys
import tempfile
import time
import unittest
import unittest.mock
import zipfile
from pathlib import Path

HALCYON = Path(__file__).resolve().parent.parent / "dots/.config/hypr/hyprland/halcyon"
sys.path.insert(0, str(HALCYON))
import halcyon_fonts as fonts  # noqa: E402


class FontsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.patches = [unittest.mock.patch.object(fonts, "FONTS", self.root / "fonts/halcyon-imported"),
                        unittest.mock.patch.object(fonts, "refresh_cache")]
        for patch in self.patches:
            patch.start()
        (self.root / "Downloads").mkdir()

    def tearDown(self):
        for patch in self.patches:
            patch.stop()
        self.tmp.cleanup()

    def make_zip(self, name, members):
        path = self.root / "Downloads" / name
        with zipfile.ZipFile(path, "w") as archive:
            for member, data in members.items():
                archive.writestr(member, data)
        return path

    def test_a_family_zip_lands_in_one_folder(self):
        path = self.make_zip("SomeFamily.zip", {
            "Some Family/OTF/SomeFamily-Regular.otf": b"otf", "Some Family/WOFF2/SomeFamily-Bold.woff2": b"w2",
            "Some Family/License.pdf": b"pdf", "__MACOSX/._SomeFamily-Regular.otf": b"junk"})
        [(name, count)] = fonts.install([path])
        self.assertEqual((name, count), ("somefamily", 2))
        self.assertEqual(sorted(fonts.installed()["somefamily"]), ["SomeFamily-Bold.woff2", "SomeFamily-Regular.otf"])

    def test_a_zip_can_never_write_outside_its_folder(self):
        path = self.make_zip("evil.zip", {"../../../escaped.ttf": b"x", "/abs/also.ttf": b"y"})
        fonts.install([path])
        self.assertFalse((self.root / "escaped.ttf").exists())
        self.assertEqual(sorted(fonts.installed()["evil"]), ["also.ttf", "escaped.ttf"])

    def test_a_zip_without_fonts_is_refused_and_leaves_nothing(self):
        path = self.make_zip("notes.zip", {"readme.txt": b"hi"})
        with self.assertRaises(fonts.FontError):
            fonts.install([path])
        self.assertEqual(fonts.installed(), {})

    def test_single_files_and_removal(self):
        font = self.root / "Inter-Regular.ttf"
        font.write_bytes(b"ttf")
        fonts.install([font])
        self.assertIn("inter", fonts.installed())
        fonts.remove("inter")
        self.assertNotIn("inter", fonts.installed())
        with self.assertRaises(fonts.FontError):
            fonts.remove("inter")

    def test_other_files_are_refused(self):
        other = self.root / "photo.png"
        other.write_bytes(b"png")
        with self.assertRaises(fonts.FontError):
            fonts.install([other])

    def test_right_font_comes_from_halcyons_copy(self):
        with unittest.mock.patch.object(fonts, "RIGHT_FONT_DIR", self.root / "fonts/halcyon-rightfont"), \
                unittest.mock.patch.object(fonts.shutil, "which", return_value=None), \
                unittest.mock.patch.object(fonts, "fetch") as fetch:
            fonts.install_right_font()
            fetch.assert_not_called()
        installed = self.root / "fonts/halcyon-rightfont"
        self.assertEqual((installed / fonts.RIGHT_FONT_FILE).read_bytes()[:4], b"\x00\x01\x00\x00")
        self.assertIn("SIL Open Font License", (installed / "OFL.txt").read_text())

    def test_latest_follows_the_site_to_the_font_file(self):
        pages = {
            "https://www.rightofthebell.com/fonts": b'<script type="module" src="/assets/index-AB12.js"></script>',
            "https://www.rightofthebell.com/assets/index-AB12.js": b'x=()=>import("./FontLab-Z9.js")',
            "https://www.rightofthebell.com/assets/FontLab-Z9.js": b'a="/assets/RightFont-Review-v8--Q1.ttf",b="x"',
            "https://www.rightofthebell.com/assets/RightFont-Review-v8--Q1.ttf": b"\x00\x01\x00\x00font",
        }
        with unittest.mock.patch.object(fonts, "RIGHT_FONT_DIR", self.root / "fonts/halcyon-rightfont"), \
                unittest.mock.patch.object(fonts.shutil, "which", return_value=None), \
                unittest.mock.patch.object(fonts, "fetch", side_effect=lambda url: pages[url]):
            self.assertEqual(fonts.install_right_font(latest=True),
                             "https://www.rightofthebell.com/assets/RightFont-Review-v8--Q1.ttf")
        self.assertEqual((self.root / "fonts/halcyon-rightfont" / fonts.RIGHT_FONT_FILE).read_bytes(), b"\x00\x01\x00\x00font")

    def test_latest_refuses_what_is_not_a_font(self):
        with unittest.mock.patch.object(fonts, "RIGHT_FONT_DIR", self.root / "fonts/halcyon-rightfont"), \
                unittest.mock.patch.object(fonts, "latest_right_font_url", return_value="https://x/RightFont.ttf"), \
                unittest.mock.patch.object(fonts, "fetch", return_value=b"<html>"):
            with self.assertRaises(fonts.FontError):
                fonts.install_right_font(latest=True)


class PackagingTest(unittest.TestCase):
    def test_right_font_ships_with_its_licence(self):
        folder = HALCYON.parents[3] / ".local/share/fonts/halcyon-rightfont"
        self.assertEqual((folder / "RightFont-Review-v7.ttf").read_bytes()[:4], b"\x00\x01\x00\x00")
        licence = (folder / "OFL.txt").read_text()
        self.assertIn("The Inter Project Authors", licence)
        self.assertIn("SIL OPEN FONT LICENSE Version 1.1", licence)
        installer = (HALCYON.parents[4] / "sdata/subcmd-install/3.files-legacy.sh").read_text()
        self.assertIn("fonts/halcyon-rightfont", installer)

    def test_font_manager_is_a_dependency(self):
        pkgbuild = (HALCYON.parents[4] / "sdata/dist-arch/illogical-impulse-fonts-themes/PKGBUILD").read_text()
        self.assertIn("  font-manager", pkgbuild)


if __name__ == "__main__":
    unittest.main()
