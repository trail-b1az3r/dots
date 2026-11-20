"""`halcyon fonts`: fonts and zips of them installed for the user, never outside their folder; Right Grotesk found in
Downloads, never downloaded. Run: python3 -m unittest discover -s tests"""

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
                        unittest.mock.patch.object(fonts, "refresh_cache"),
                        unittest.mock.patch.object(fonts, "downloads", return_value=self.root / "Downloads")]
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
        path = self.make_zip("RightGrotesk.zip", {
            "Right Grotesk/OTF/RightGrotesk-Regular.otf": b"otf", "Right Grotesk/WOFF2/RightGrotesk-Bold.woff2": b"w2",
            "Right Grotesk/License.pdf": b"pdf", "__MACOSX/._RightGrotesk-Regular.otf": b"junk"})
        [(name, count)] = fonts.install([path])
        self.assertEqual((name, count), ("rightgrotesk", 2))
        self.assertEqual(sorted(fonts.installed()["rightgrotesk"]), ["RightGrotesk-Bold.woff2", "RightGrotesk-Regular.otf"])

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

    def test_right_grotesk_is_the_newest_zip_in_downloads(self):
        old = self.make_zip("Right-Grotesk-old.zip", {"a.otf": b"1"})
        os.utime(old, (time.time() - 100, time.time() - 100))
        self.make_zip("right_grotesk_trial.zip", {"b.otf": b"2"})
        self.make_zip("Other.zip", {"c.otf": b"3"})
        self.assertEqual(fonts.newest_right_grotesk().name, "right_grotesk_trial.zip")

    def test_without_the_zip_it_opens_the_foundry_page_and_downloads_nothing(self):
        with unittest.mock.patch.object(fonts, "open_detached") as opened, \
                unittest.mock.patch("sys.stdout", io.StringIO()) as out:
            self.assertEqual(fonts.main(["install", "right-grotesk"]), 1)
        opened.assert_called_once_with(["xdg-open", fonts.RIGHT_GROTESK_URL])
        self.assertIn("personal use", out.getvalue())

    def test_with_the_zip_it_installs_it(self):
        self.make_zip("RightGrotesk-Trial.zip", {"RightGrotesk-Regular.otf": b"1"})
        with unittest.mock.patch("sys.stdout", io.StringIO()):
            self.assertEqual(fonts.main(["install", "right-grotesk"]), 0)
        self.assertIn("rightgrotesk-trial", fonts.installed())


class PackagingTest(unittest.TestCase):
    def test_font_manager_is_a_dependency(self):
        pkgbuild = (HALCYON.parents[4] / "sdata/dist-arch/illogical-impulse-fonts-themes/PKGBUILD").read_text()
        self.assertIn("  font-manager", pkgbuild)


if __name__ == "__main__":
    unittest.main()
