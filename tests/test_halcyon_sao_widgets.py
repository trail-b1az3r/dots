"""The Sword Art Online theme's desktop widgets: silver menu-panel cards, tile gauges, an HP-bar progress line and
a clock face of its own. Run: python3 -m unittest discover -s tests"""

import unittest
from pathlib import Path

W = Path(__file__).resolve().parent.parent / "dots/.config/quickshell/ii/modules/ii/background/widgets"
STYLES = (W / "revolver/RevolverStyles.js").read_text()
PLATE = (W / "ThemedPlate.qml").read_text()
GAUGE = (W / "ThemedGauge.qml").read_text()
PROGRESS = (W / "ThemedProgress.qml").read_text()
CLOCK = (W / "clock/ThemeClock.qml").read_text()
COOKIE = (W / "clock/CookieClock.qml").read_text()


class SaoWidgetsTest(unittest.TestCase):
    def test_the_theme_has_its_own_cards_not_silences(self):
        self.assertIn('case "sword-art-online":\n        return STYLES["sao-panel"];', STYLES)
        self.assertIn('plate: "sao"', STYLES)
        self.assertIn('readonly property bool sao: style.plate === "sao"', PLATE)

    def test_its_look_uses_tiles_and_the_hp_bar(self):
        self.assertIn('"sao-panel": { id: "sao-panel", gauge: "tiles", bars: "pill", progress: "hp"', STYLES)
        self.assertIn('gauge.kind === "tiles"', GAUGE)
        self.assertIn('bar.kind === "hp"', PROGRESS)

    def test_the_clock_has_a_face_of_its_own(self):
        self.assertIn('"sao": "sao"', COOKIE)
        self.assertIn('visible: face.kind === "sao"', CLOCK)

    def test_the_revolver_keeps_its_smoked_disc(self):
        self.assertIn('case "sword-art-online":\n        return STYLES["sao"];', STYLES)


if __name__ == "__main__":
    unittest.main()
