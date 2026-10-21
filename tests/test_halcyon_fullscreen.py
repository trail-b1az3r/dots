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


class FullscreenWindowsTest(unittest.TestCase):
    HALCYON = ROOT / "dots/.config/hypr/hyprland/halcyon"

    def test_the_music_strip_stays_behind_a_fullscreen_window_by_default(self):
        # It is 12% of the screen, drawn over the window: the slice that "gets cut off" in a fullscreen app.
        text = read(self.HALCYON / "plus.lua")
        self.assertRegex(text, r"if caps\.stripFullscreen then\s+hl\.config\(\{\s+superposition = \{\s+over_fullscreen = false,")

    def test_dropping_a_window_at_the_top_is_on_by_default_and_asks_the_build_first(self):
        text = read(self.HALCYON / "plus.lua")
        self.assertRegex(text, r"if caps\.dragEdge then\s+hl\.config\(\{\s+binds = \{\s+drag_fullscreen_edge = 8,")
        compositor = read(self.HALCYON / "compositor.lua")
        self.assertIn('hasOption("binds:drag_fullscreen_edge")', compositor)
        self.assertIn('hasOption("superposition:over_fullscreen")', compositor)

    def test_the_animated_wallpaper_rests_while_hidden_and_wakes_when_it_is_not(self):
        sleep = read(II / "modules/ii/background/WallpaperSleep.qml")
        self.assertIn('"pkill", "-STOP", "-x", "mpvpaper"', sleep)
        self.assertIn('"pkill", "-CONT", "-x", "mpvpaper"', sleep)
        self.assertIn("GlobalStates.screenLocked", sleep)
        self.assertIn("screens.every(", sleep, "covered on every monitor, not just one")
        self.assertIn("onEnabledChanged: if (!enabled) wake()", sleep, "turning it off must not leave it stopped")
        self.assertIn("WallpaperSleep {}", read(II / "panelFamilies/IllogicalImpulseFamily.qml"))
        self.assertIn("pauseVideoWhenHidden", read(II / "modules/common/Config.qml"))
        self.assertIn("pauseVideoWhenHidden", read(II / "modules/settings/BackgroundConfig.qml"))

    def test_the_spectrum_stops_while_the_screen_is_locked(self):
        self.assertIn("users > 0 && !GlobalStates.screenLocked", read(II / "services/AudioSpectrum.qml"))
