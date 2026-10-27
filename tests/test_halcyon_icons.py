"""The anime themes' icon packs (halcyon_icons.py): every installed app's icon redrawn in the theme's frame, from a
stand-in icon theme and stand-in .desktop files, with the real ImageMagick when it is here.
Run: python3 -m unittest discover -s tests"""

import importlib
import os
import shutil
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HALCYON = ROOT / "dots/.config/hypr/hyprland/halcyon"
sys.path.insert(0, str(HALCYON))
import halcyon_icons as icons  # noqa: E402
import subprocess  # noqa: E402


def magick_draws_svg():
    """Whether the ImageMagick here can read SVG (Arch's has librsvg built in; some distributions' builds can't)."""
    tool = shutil.which("magick") or shutil.which("convert")
    if not tool:
        return False
    with tempfile.TemporaryDirectory() as folder:
        svg = Path(folder, "t.svg")
        svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8"><rect width="8" height="8"/></svg>')
        done = subprocess.run([tool, str(svg), str(Path(folder, "t.png"))], capture_output=True, check=False)
        return done.returncode == 0

SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48"><rect x="6" y="6" width="36" height="36" '
       'fill="#3080ff"/><circle cx="24" cy="24" r="9" fill="#ffffff"/></svg>')


class IconPackTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        theme = base / "icons/Base"
        (theme / "scalable/apps").mkdir(parents=True)
        (theme / "48x48/apps").mkdir(parents=True)
        (theme / "index.theme").write_text("[Icon Theme]\nName=Base\nDirectories=scalable/apps\n")
        (theme / "scalable/apps/firefox.svg").write_text(SVG)
        (theme / "48x48/apps/firefox.png").write_text("small")
        (theme / "scalable/apps/folder.svg").write_text(SVG)
        (theme / "scalable/apps/firefox-symbolic.svg").write_text(SVG)
        apps = base / "applications"
        apps.mkdir()
        (apps / "firefox.desktop").write_text("[Desktop Entry]\nName=Firefox\nIcon=firefox\n")
        (apps / "hidden.desktop").write_text("[Desktop Entry]\nName=Hidden\nIcon=hidden-app\nNoDisplay=true\n")
        (apps / "gone.desktop").write_text("[Desktop Entry]\nName=Gone\nIcon=no-such-icon\n")
        patches = {"DATA": base / "data", "STATE": base / "state", "PREVIOUS": base / "state/before.txt",
                   "ICON_DIRS": [base / "icons"], "PIXMAPS": [], "APP_DIRS": [apps]}
        for name, value in patches.items():
            patcher = unittest.mock.patch.object(icons, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_apps_come_from_the_desktop_files_that_show(self):
        self.assertEqual(icons.app_icons(), ["firefox", "no-such-icon"])

    def test_the_scalable_icon_wins_and_symbolic_ones_are_skipped(self):
        found = icons.find_icon("firefox", icons.search_order("Base"))
        self.assertEqual(found.name, "firefox.svg")
        self.assertIsNone(icons.find_icon("no-such-icon", icons.search_order("Base")))

    def test_frames_are_drawn(self):
        self.assertIn("#5CD6F2", icons.frame_svg("icey"))
        light, dark = icons.frame_svg("ink"), icons.frame_svg("ink-dark")
        self.assertIn(f'fill="{icons.PAPER}" stroke="{icons.INK}"', light)
        self.assertIn(f'stroke="{icons.PAPER}"', dark, "the dark pack is the light one in negative")

    @unittest.skipUnless(magick_draws_svg(), "no ImageMagick that reads SVG")
    def test_a_pack_is_made_and_inherits_the_rest(self):
        result = icons.make("ink", base="Base", quiet=True)
        out = Path(result["path"])
        made = sorted(p.name for p in (out / "128x128/apps").glob("*.png"))
        self.assertEqual(made, ["firefox.png", "folder.png"])
        self.assertEqual(result["icons"], 2)
        index = (out / "index.theme").read_text()
        self.assertIn("Inherits=Base,hicolor", index)
        self.assertEqual(out.name, "Halcyon-Manga-Ink")

    def test_apply_remembers_the_icons_in_use_and_restore_puts_them_back(self):
        current = {"name": "Papirus-Dark"}
        (icons.DATA / "icons/Halcyon-After-ICEY").mkdir(parents=True)
        (icons.DATA / "icons/Halcyon-After-ICEY/index.theme").write_text("[Icon Theme]\n")
        with unittest.mock.patch.object(icons, "current_icon_theme", side_effect=lambda: current["name"]), \
                unittest.mock.patch.object(icons, "set_icon_theme", side_effect=lambda n: current.update(name=n)):
            icons.apply("icey")
            self.assertEqual(current["name"], "Halcyon-After-ICEY")
            icons.apply("icey")   # again: what was in use before is still Papirus, not the pack
            self.assertEqual(icons.read_previous(), "Papirus-Dark")
            icons.restore()
            self.assertEqual(current["name"], "Papirus-Dark")

    def test_themes_with_packs(self):
        self.assertEqual(icons.THEME_PACKS, {"after-icey": "icey", "manga-ink": "ink", "manga-ink-dark": "ink-dark"})


if __name__ == "__main__":
    unittest.main()
