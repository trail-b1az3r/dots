"""The calendar alarm: the sounds made by scripts/alarm/alarm_sounds.py (checked by ear's numbers: pitch, pattern,
length), and the pieces that ring them. Run: python3 -m unittest discover -s tests"""

import math
import struct
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
II = ROOT / "dots/.config/quickshell/ii"
TOOL = II / "scripts/alarm/alarm_sounds.py"


def samples(path):
    with wave.open(str(path)) as w:
        rate, frames = w.getframerate(), w.readframes(w.getnframes())
        assert (w.getnchannels(), w.getsampwidth()) == (1, 2)
    return rate, [v / 32768 for v in struct.unpack(f"<{len(frames) // 2}h", frames)]


def pitch(values, rate):
    """The dominant frequency, from upward zero crossings."""
    ups = sum(1 for a, b in zip(values, values[1:]) if a <= 0 < b)
    return ups * rate / len(values)


def loud(values, rate, start, end):
    part = values[int(start * rate):int(end * rate)]
    return math.sqrt(sum(v * v for v in part) / max(1, len(part)))


class SoundsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name) / "sounds"
        out = subprocess.run([sys.executable, str(TOOL), "ensure", str(cls.dir)], capture_output=True, text=True, check=True)
        cls.written = out.stdout.split()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_all_four_are_written_once(self):
        self.assertEqual(sorted(Path(p).name for p in self.written), ["beep.wav", "chime.wav", "smoke.wav", "tornado.wav"])
        again = subprocess.run([sys.executable, str(TOOL), "ensure", str(self.dir)], capture_output=True, text=True, check=True)
        self.assertEqual(again.stdout, "", "ensure leaves sounds that are there alone")

    def test_smoke_alarm_is_three_high_beeps_then_a_long_gap(self):
        rate, v = samples(self.dir / "smoke.wav")
        self.assertAlmostEqual(len(v) / rate, 4.0, places=2)
        for start in (0.0, 1.0, 2.0):          # the beeps
            self.assertGreater(loud(v, rate, start + 0.1, start + 0.4), 0.3)
            self.assertAlmostEqual(pitch(v[int((start + 0.05) * rate):int((start + 0.45) * rate)], rate), 3150, delta=120)
        for start, end in ((0.55, 0.95), (1.55, 1.95), (2.55, 3.95)):   # the gaps, the last one long
            self.assertLess(loud(v, rate, start, end), 0.001)

    def test_tornado_siren_winds_up_and_down(self):
        rate, v = samples(self.dir / "tornado.wav")
        self.assertGreater(len(v) / rate, 7)
        first, top, last = (pitch(v[int(a * rate):int(b * rate)], rate) for a, b in ((0.0, 0.5), (4.6, 5.2), (7.8, 8.2)))
        self.assertLess(first, 320)
        self.assertGreater(top, 550)
        self.assertLess(last, 320)
        self.assertGreater(loud(v, rate, 4.6, 5.2), loud(v, rate, 0.0, 0.5), "louder at the top of the wail")

    def test_nothing_clips(self):
        for name in ("smoke", "tornado", "beep", "chime"):
            _, v = samples(self.dir / f"{name}.wav")
            self.assertLess(max(abs(x) for x in v), 1.0, name)


class WiringTest(unittest.TestCase):
    def read(self, rel):
        return (II / rel).read_text(encoding="utf-8")

    def test_events_ring_their_alarm_and_snoozes_come_back(self):
        events = self.read("services/CalendarEvents.qml")
        self.assertIn('item.kind === "alarm"', events)
        self.assertIn("Alarm.ring({ id: e.id, title: e.title, time: e.time })", events)
        self.assertIn("function onSnoozed(id, minutes)", events)
        self.assertIn("interval: 5000", events, "checked often enough to ring on time")

    def test_the_alarm_starts_with_a_smoke_alarm_then_a_tornado_siren(self):
        config = self.read("modules/common/Config.qml")
        self.assertIn('property string firstSound: "smoke"', config)
        self.assertIn('property string secondSound: "tornado"', config)
        alarm = self.read("services/Alarm.qml")
        self.assertIn("root.play(root.settings.firstSound)", alarm)
        self.assertIn("root.play(second)", alarm)
        # silent is a choice, and plays nothing
        self.assertIn('value === "silent"', alarm)

    def test_it_is_shown_on_every_screen_whatever_the_panels(self):
        shell = self.read("shell.qml")
        self.assertIn("AlarmOverlay {}", shell)
        # Beside shell.qml, not in a folder of its own: a live reload does not see a folder that is new since the
        # shell started, and "AlarmOverlay is not a type" broke the whole shell after the update that added it.
        self.assertTrue((II / "AlarmOverlay.qml").is_file())
        self.assertNotIn('import "modules/ii/alarm"', shell)
        self.assertIn("Alarm.load()", shell)
        overlay = self.read("AlarmOverlay.qml")
        self.assertIn("WlrLayer.Overlay", overlay)
        self.assertIn("Alarm.stop()", overlay)
        self.assertIn("Alarm.snooze()", overlay)

    def test_the_calendar_and_settings_offer_it(self):
        self.assertIn("CalendarEvents.setAlarm", self.read("modules/ii/sidebarRight/calendar/CalendarDayPanel.qml"))
        self.assertIn('"alarm", "test"', self.read("modules/settings/GeneralConfig.qml"))


if __name__ == "__main__":
    unittest.main()
