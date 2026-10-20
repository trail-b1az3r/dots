"""Fullscreen: what hides the wallpaper and the screen corners is the compositor's own fullscreen state on
that monitor, never another monitor's window or an app that was only told it is fullscreen.
Run: python3 -m unittest discover -s tests"""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
II = ROOT / "dots/.config/quickshell/ii"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class FullscreenTest(unittest.TestCase):
    def function_body(self, source: str, name: str) -> str:
        start = source.index(f"function {name}(")
        depth, i = 0, source.index("{", start)
        begin = i
        while True:
            depth += {"{": 1, "}": -1}.get(source[i], 0)
            i += 1
            if depth == 0:
                return source[begin:i]

    def test_the_compositor_check_reads_only_the_compositors_state_of_this_monitors_workspace(self):
        body = self.function_body(read(II / "services/HyprlandData.qml"), "compositorFullscreenOnMonitor")
        self.assertIn("activeWorkspace", body, "the monitor's own workspace")
        self.assertIn("isFullscreenState(win.fullscreen)", body)
        self.assertNotIn("fullscreenClient", body, "an app only told it is fullscreen stays windowed")

    def test_the_wallpaper_and_the_corners_use_it(self):
        for path in ("modules/ii/background/Background.qml", "modules/ii/screenCorners/ScreenCorners.qml"):
            text = read(II / path)
            self.assertIn("compositorFullscreenOnMonitor(modelData.name)", text, path)
            self.assertNotIn("window.wayland?.fullscreen", text, f"{path} still asks the toplevel list")

    def test_themes_do_not_draw_corners_over_a_fullscreen_app(self):
        # 1 draws the rounded corners always, over fullscreen windows too, which cuts their corners off.
        def values(node, key):
            if isinstance(node, dict):
                for name, value in node.items():
                    if name == key:
                        yield value
                    yield from values(value, key)

        seen = 0
        for theme in (ROOT / "dots/.config/hypr/hyprland/halcyon/themes").glob("*.json"):
            for value in values(json.loads(read(theme)), "appearance.fakeScreenRounding"):
                seen += 1
                self.assertNotEqual(value, 1, f"{theme.name} forces the corners over fullscreen windows")
        self.assertGreater(seen, 0, "HyperNeo sets it, so the search should find at least one")

    def test_the_default_hides_the_corners_in_fullscreen(self):
        match = re.search(r"fakeScreenRounding:\s*(\d)", read(II / "modules/common/Config.qml"))
        self.assertEqual(match.group(1), "2")


if __name__ == "__main__":
    unittest.main()
