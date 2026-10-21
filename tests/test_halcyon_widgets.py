"""The desktop widgets added with the audio visualizer: its cava config, its options, its loaders and the rule that
keeps its window on the superposition strip. The QML itself is rendered in a real Quickshell outside these tests.
Run: python3 -m unittest discover -s tests"""

import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
II = ROOT / "dots/.config/quickshell/ii"
WIDGETS = II / "modules/ii/background/widgets"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class SpectrumServiceTest(unittest.TestCase):
    def script(self) -> str:
        source = read(II / "services/AudioSpectrum.qml")
        block = re.search(r"readonly property string script: (.*?)\n\n", source, re.S).group(1)
        # The QML string literals, joined, with QML's escapes undone: the bash text.
        return "".join(re.findall(r"'((?:[^'\\]|\\.)*)'", block)).replace("\\\\", "\\")

    def run_script(self, bars: str, fps: str) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            stub = Path(tmp) / "cava"
            stub.write_text('#!/bin/sh\ncat "$2"\n')
            stub.chmod(0o755)
            env = {**os.environ, "PATH": f"{tmp}:{os.environ['PATH']}", "XDG_RUNTIME_DIR": tmp}
            done = subprocess.run(["bash", "-c", self.script(), "_", bars, fps], capture_output=True, text=True, env=env,
                                  timeout=30)
            self.assertEqual(done.returncode, 0, done.stderr)
            return done.stdout

    def test_cava_is_given_the_bar_count_and_the_frame_rate(self):
        config = self.run_script("64", "45")
        self.assertIn("bars = 64\n", config)
        self.assertIn("framerate = 45\n", config)

    def test_cava_prints_one_ascii_line_of_values_to_read(self):
        config = self.run_script("32", "30")
        for line in ("method = raw", "raw_target = /dev/stdout", "data_format = ascii", "ascii_max_range = 1000",
                     "channels = mono"):
            self.assertIn(line, config)

    def test_the_two_numbers_are_not_swapped(self):
        # The script takes (bars, framerate) and writes framerate first; a swap would run 48 fps with 30 bars.
        config = self.run_script("48", "25")
        self.assertRegex(config, r"framerate = 25\n.*\nbars = 48\n")

    def test_cava_only_runs_while_something_wants_the_spectrum(self):
        source = read(II / "services/AudioSpectrum.qml")
        self.assertIn("running: root.active", source)
        self.assertIn("readonly property bool active: users > 0", source)

    def test_whatever_draws_it_counts_itself_and_leaves_when_it_goes(self):
        use = read(II / "services/SpectrumUse.qml")
        self.assertIn("AudioSpectrum.users++", use)
        self.assertIn("AudioSpectrum.users--", use)
        self.assertIn("Component.onDestruction", use)
        for widget in ("VisualizerWidget.qml", "VisualizerWindow.qml"):
            self.assertIn("SpectrumUse {", read(WIDGETS / "visualizer" / widget), widget)


class OptionsTest(unittest.TestCase):
    def widget_block(self, name: str) -> str:
        config = read(II / "modules/common/Config.qml")
        start = config.index(f"property JsonObject {name}: JsonObject {{")
        return config[start:config.index("\n                    }", start)]

    def test_the_visualizer_has_its_settings_and_is_off_by_default(self):
        block = self.widget_block("visualizer")
        for option in ('property bool enable: false', 'property string style: "bars"', "property int bars: 48",
                       "property int fps: 30", "property bool panel: false", "property bool hideWhenSilent: false",
                       "property bool asWindow: false", 'property string placementStrategy: "free"'):
            self.assertIn(option, block)

    def test_the_new_widgets_are_off_by_default_and_can_be_placed(self):
        for name in ("system", "nowPlaying"):
            block = self.widget_block(name)
            self.assertIn("property bool enable: false", block, name)
            self.assertIn("property real x:", block)
            self.assertIn("property real y:", block)

    def test_every_option_the_widgets_read_exists(self):
        config = self.widget_block("visualizer")
        for widget in ("VisualizerWidget.qml", "VisualizerWindow.qml"):
            for option in set(re.findall(r"settings\.(\w+)", read(WIDGETS / "visualizer" / widget))):
                self.assertRegex(config, rf"property \w+ {option}:", f"{widget} reads settings.{option}")


class LoadingTest(unittest.TestCase):
    def test_the_background_loads_each_widget_when_it_is_enabled(self):
        background = read(II / "modules/ii/background/Background.qml")
        self.assertIn("widgets.visualizer.enable && !Config.options.background.widgets.visualizer.asWindow", background)
        self.assertIn("sourceComponent: VisualizerWidget {", background)
        self.assertIn("shown: Config.options.background.widgets.system.enable", background)
        self.assertIn("shown: Config.options.background.widgets.nowPlaying.enable", background)
        for module in ("visualizer", "system", "nowplaying"):
            self.assertIn(f"import qs.modules.ii.background.widgets.{module}", background)

    def test_as_a_window_the_family_loads_the_window_and_the_desktop_widget_steps_aside(self):
        family = read(II / "panelFamilies/IllogicalImpulseFamily.qml")
        self.assertRegex(family, r"extraCondition: Config\.options\.background\.widgets\.visualizer\.enable && "
                                 r"Config\.options\.background\.widgets\.visualizer\.asWindow")
        self.assertIn("component: VisualizerWindow {}", family)

    def test_the_window_title_is_what_the_rule_matches(self):
        title = re.search(r'title: "([^"]+)"', read(WIDGETS / "visualizer/VisualizerWindow.qml")).group(1)
        rules = read(ROOT / "dots/.config/hypr/hyprland/halcyon/app_rules.lua")
        self.assertIn(f'{{ title = "^{title}$", superposition = true }}', rules)

    def test_every_widget_file_is_a_widget_the_canvas_can_place(self):
        for path in ("visualizer/VisualizerWidget.qml", "system/SystemWidget.qml", "nowplaying/NowPlayingWidget.qml"):
            text = read(WIDGETS / path)
            self.assertIn("AbstractBackgroundWidget {", text, path)
            self.assertRegex(text, r'configEntryName: "(visualizer|system|nowPlaying)"', path)

    def test_the_settings_page_has_a_section_for_each(self):
        page = read(II / "modules/settings/BackgroundConfig.qml")
        for title in ("Widget: Audio visualizer", "Widget: System", "Widget: Now playing"):
            self.assertIn(f'Translation.tr("{title}")', page)
        for style in ("bars", "mirror", "wave", "ring"):
            self.assertIn(f'value: "{style}"', page)
        self.assertIn("As a window (superposition)", page)

    def test_the_view_draws_the_four_styles_the_settings_offer(self):
        view = read(WIDGETS / "visualizer/SpectrumView.qml")
        for style in ("bars", "mirror", "wave", "ring"):
            self.assertIn(f'"{style}"', view)
        self.assertNotIn("Canvas", view, "scene graph items, not a canvas repainted every frame")


if __name__ == "__main__":
    unittest.main()
