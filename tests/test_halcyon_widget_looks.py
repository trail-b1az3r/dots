"""Every Halcyon theme gives the wallpaper widgets a look of its own (RevolverStyles.lookFor), and every kind of
gauge, bar, progress line and lyric mark a look names is one the widgets know how to draw.
Run: python3 -m unittest discover -s tests"""

import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
II = ROOT / "dots/.config/quickshell/ii"
WIDGETS = II / "modules/ii/background/widgets"
STYLES = WIDGETS / "revolver/RevolverStyles.js"
THEMES = ROOT / "dots/.config/hypr/hyprland/halcyon/themes"
NODE = shutil.which("node")

# Each field, the file that draws it, and how a kind shows up there.
DRAWN_BY = {
    "gauge": (["ThemedGauge.qml", "system/SystemWidget.qml"], 'gauge.kind === "{}"', 'look.spec.gauge === "{}"'),
    "bars": (["visualizer/SpectrumView.qml"], 'root.barStyle === "{}"', None),
    "progress": (["ThemedProgress.qml"], 'bar.kind === "{}"', None),
    "lyric": (["lyrics/LyricsWidget.qml"], 'root.mark === "{}"', None),
}
# The plain kinds are what a widget draws when nothing special is asked for.
PLAIN = {"gauge": "ring", "bars": "round", "progress": "line", "lyric": "plain"}


def looks() -> dict:
    source = STYLES.read_text(encoding="utf-8").replace(".pragma library", "", 1)
    themes = [""] + sorted(p.stem for p in THEMES.glob("*.json"))
    script = source + f"\nconsole.log(JSON.stringify(Object.fromEntries({json.dumps(themes)}.map(t => [t, lookFor(t)]))))"
    out = subprocess.run([NODE, "-e", script], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


@unittest.skipUnless(NODE, "node is not installed")
class LookTests(unittest.TestCase):
    def setUp(self):
        self.looks = looks()

    def test_every_shipped_theme_has_a_look_of_its_own(self):
        themed = {theme: look["id"] for theme, look in self.looks.items() if theme}
        self.assertNotIn("default", themed.values(), themed)
        self.assertEqual(self.looks[""]["id"], "default")
        # no two looks are the same apart from their name
        distinct = {json.dumps({k: v for k, v in look.items() if k != "id"}, sort_keys=True) for look in self.looks.values()}
        self.assertEqual(len(distinct), len({look["id"] for look in self.looks.values()}))

    def test_every_kind_a_look_names_is_drawn(self):
        for field, (files, pattern, alt) in DRAWN_BY.items():
            text = "".join((WIDGETS / f).read_text(encoding="utf-8") for f in files)
            for theme, look in self.looks.items():
                kind = look[field]
                if kind == PLAIN[field]:
                    continue
                found = pattern.format(kind) in text or (alt and alt.format(kind) in text)
                self.assertTrue(found, f"{theme or 'no theme'}: {field} '{kind}' is not drawn in {files}")

    def test_fixed_colours_are_colours(self):
        for theme, look in self.looks.items():
            for key in ("colorA", "colorB", "text", "glow"):
                self.assertRegex(look[key], r"^(#[0-9a-fA-F]{6})?$", f"{theme}: {key}")


class WiringTests(unittest.TestCase):
    def test_each_widget_follows_the_look(self):
        for path in ("system/SystemWidget.qml", "nowplaying/NowPlayingWidget.qml", "visualizer/VisualizerWidget.qml",
                     "visualizer/VisualizerWindow.qml", "lyrics/LyricsWidget.qml", "weather/WeatherWidget.qml",
                     "clock/CookieClock.qml"):
            self.assertIn("ThemeLook {}", (WIDGETS / path).read_text(encoding="utf-8"), path)


if __name__ == "__main__":
    unittest.main()
