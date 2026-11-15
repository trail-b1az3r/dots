"""The Sword Art Online theme's desktop widgets: no background (they stand on the wallpaper), tile gauges, an HP-bar
progress line, a clock of its own and a revolver that is only its ring. Run: python3 -m unittest discover -s tests"""

import unittest
from pathlib import Path

W = Path(__file__).resolve().parent.parent / "dots/.config/quickshell/ii/modules/ii/background/widgets"
STYLES = (W / "revolver/RevolverStyles.js").read_text()
PLATE = (W / "ThemedPlate.qml").read_text()
GAUGE = (W / "ThemedGauge.qml").read_text()
PROGRESS = (W / "ThemedProgress.qml").read_text()
CLOCK = (W / "clock/ThemeClock.qml").read_text()
COOKIE = (W / "clock/CookieClock.qml").read_text()
DRUM = (W / "revolver/RevolverDrum.qml").read_text()


class SaoWidgetsTest(unittest.TestCase):
    def test_the_widgets_have_no_background(self):
        self.assertIn('case "sword-art-online":\n        return STYLES["sao-panel"];', STYLES)
        self.assertIn('plate: "sao"', STYLES)
        self.assertIn("visible: !plate.manga && !plate.sao", PLATE)
        self.assertNotIn("Styles.circle(face.c, face.c, 109)", CLOCK)
        self.assertIn('third: "#D5DDE6", bare: true', STYLES)
        self.assertIn('drum.style.bare ? "" : Styles.circle(drum.c, drum.c, 108)', DRUM)

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
