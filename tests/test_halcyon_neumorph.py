"""The Neumorph theme: soft surfaces pressed out of the page (common/neu), the Islands bar, and Open Runde, installed
from MacShell's copy the first time the theme is applied. Run: python3 -m unittest discover -s tests"""

import importlib.machinery
import importlib.util
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "dots/.config"
HALCYON = CONFIG / "hypr/hyprland/halcyon"
NEU = CONFIG / "quickshell/ii/modules/common/neu"
_loader = importlib.machinery.SourceFileLoader("halcyon_theme_neumorph", str(HALCYON / "halcyon-theme"))
_spec = importlib.util.spec_from_loader("halcyon_theme_neumorph", _loader)
theme = importlib.util.module_from_spec(_spec)
_loader.exec_module(theme)


class NeumorphThemeTest(unittest.TestCase):
    def test_valid_with_islands_and_its_font(self):
        data = theme.load("neumorph")
        self.assertEqual(data["mode"], "light")
        self.assertEqual(data["shell_config"]["bar.cornerStyle"], 3)
        self.assertEqual(data["shell_config"]["appearance.fonts.main"], "Open Runde")
        # The surfaces are opaque clay: glass panels would show the wallpaper through them.
        self.assertIs(data["shell_config"]["appearance.transparency.enable"], False)
        self.assertTrue(theme.resolve_wallpaper(data).is_file())

    def test_the_shader_ships_compiled_for_opengl_and_the_rest(self):
        for name in ("neumorph.frag", "neu.vert"):
            self.assertTrue((NEU / "shaders" / name).is_file(), name)
            self.assertTrue((NEU / "shaders" / (name + ".qsb")).is_file(), name + ".qsb")
        source = (NEU / "Neu.qml").read_text()
        self.assertIn('vertexShader: Qt.resolvedUrl("shaders/neu.vert.qsb")', source)

    def test_the_dock_bar_and_plates_draw_it(self):
        modules = CONFIG / "quickshell/ii/modules/ii"
        self.assertIn('frame.kind === "neu"', (modules / "dock/DockFrame.qml").read_text())
        self.assertIn('style.plate === "neu"', (modules / "background/widgets/ThemedPlate.qml").read_text())
        self.assertIn('=== "neumorph"', (modules / "bar/BarGroup.qml").read_text())
        styles = (modules / "background/widgets/revolver/RevolverStyles.js").read_text()
        self.assertIn('"neumorph": "neu"', styles)


class FontsTest(unittest.TestCase):
    def test_open_runde_is_installed_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            with unittest.mock.patch.object(theme, "DATA", data), \
                    unittest.mock.patch.object(theme.shutil, "which", return_value=None):
                self.assertTrue(theme.ensure_fonts(theme.load("neumorph")))
                self.assertTrue((data / "fonts/halcyon/OpenRunde-Regular.otf").is_file())
                self.assertFalse(theme.ensure_fonts(theme.load("neumorph")), "already there")

    def test_a_theme_without_bundled_fonts_installs_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            with unittest.mock.patch.object(theme, "DATA", Path(tmp)):
                self.assertFalse(theme.ensure_fonts(theme.load("red-sun")))
            self.assertFalse((Path(tmp) / "fonts").exists())


if __name__ == "__main__":
    unittest.main()
