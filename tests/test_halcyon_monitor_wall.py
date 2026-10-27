"""The wall between monitors in the shell: MonitorWall.qml's bulge (run under node) sits on the edge hyprland-plus
names, where it names, and grows inward; the Plus settings write plus:monitor_wall only for a hyprland-plus that has it.
Run: python3 -m unittest discover -s tests"""

import json
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QML = ROOT / "dots/.config/quickshell/ii/modules/ii/monitorWall/MonitorWall.qml"
sys.path.insert(0, str(ROOT / "dots/.config/hypr/hyprland/halcyon"))
import halcyon_plus_settings as ps  # noqa: E402

NODE = shutil.which("node")


def points(edge, start, length, depth, w=1920, h=1080):
    body = re.search(r"(function bulgePath\(.*?\n    \})", QML.read_text(), re.S).group(1)
    script = body + f"\nconsole.log(JSON.stringify(bulgePath(...{json.dumps([edge, start, length, depth, w, h])})))"
    path = json.loads(subprocess.run([NODE, "-e", script], capture_output=True, text=True, check=True).stdout)
    numbers = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", path)]
    return list(zip(numbers[0::2], numbers[1::2]))


@unittest.skipUnless(NODE, "node is not installed")
class BulgeTest(unittest.TestCase):
    def test_left_edge(self):
        pts = points("left", 200, 600, 50)
        self.assertEqual(min(x for x, _ in pts), 0, "it starts on the edge")
        self.assertEqual(max(x for x, _ in pts), 50, "and comes in as deep as pushed")
        ys = [y for _, y in pts]
        self.assertLess(min(ys), 200)
        self.assertGreater(max(ys), 800, "a little wider than the window")

    def test_right_and_bottom_edges_come_inward(self):
        self.assertEqual(min(x for x, _ in points("right", 200, 600, 40)), 1880)
        self.assertEqual(min(y for _, y in points("bottom", 300, 500, 30)), 1050)

    def test_top_edge_runs_along_x(self):
        pts = points("top", 400, 300, 20)
        self.assertEqual(max(y for _, y in pts), 20)
        self.assertGreater(max(x for x, _ in pts), 700)


class SettingsTest(unittest.TestCase):
    def test_monitor_wall_setting(self):
        values, _ = ps.resolve({"monitorWall": 200})
        self.assertEqual(values["monitorWall"], 200)
        self.assertEqual(ps.SETTINGS["monitorWall"][0], "plus.monitor_wall")
        self.assertEqual(ps.SETTINGS["monitorWall"][5], "plus:monitor_wall", "only for a hyprland-plus that has it")


class WiringTest(unittest.TestCase):
    def test_loaded_with_more_than_one_monitor(self):
        family = (ROOT / "dots/.config/quickshell/ii/panelFamilies/IllogicalImpulseFamily.qml").read_text()
        self.assertIn("component: MonitorWall {}", family)


if __name__ == "__main__":
    unittest.main()
