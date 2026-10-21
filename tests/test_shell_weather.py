"""The shell's weather (services/Weather.qml): it works without jq, and without an answer from location services.
Run: python3 -m unittest discover -s tests"""

import unittest
from pathlib import Path

WEATHER = Path(__file__).resolve().parent.parent / "dots/.config/quickshell/ii/services/Weather.qml"


class WeatherTest(unittest.TestCase):
    def test_no_jq(self):
        # jq is often not installed; piping into it left the weather at "--°" for good.
        text = WEATHER.read_text()
        self.assertNotIn("jq", text.replace("needs no jq", "").replace("jq isn't needed", ""))
        self.assertIn("current_condition?.[0]", text)
        self.assertIn("nearest_area?.[0]", text)

    def test_a_silent_gps_falls_back_to_the_city(self):
        text = WEATHER.read_text()
        self.assertIn("running: root.gpsActive && !root.location.valid", text)
        self.assertIn("root.gpsActive = false", text)


if __name__ == "__main__":
    unittest.main()
