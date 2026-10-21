"""Synced lyrics: the LRC parser and the lookup, run with node against the same .js file the shell loads.
Run: python3 -m unittest discover -s tests"""

import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
II = ROOT / "dots/.config/quickshell/ii"
PARSE = II / "modules/ii/background/widgets/lyrics/LyricsParse.js"
NODE = shutil.which("node")


def run_js(expression: str):
    """Evaluate `expression` with the library's functions in scope; the first line, `.pragma library`, is QML's."""
    source = PARSE.read_text(encoding="utf-8").replace(".pragma library", "", 1)
    out = subprocess.run([NODE, "-e", source + f"\nconsole.log(JSON.stringify({expression}))"],
                         capture_output=True, text=True, check=False)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


@unittest.skipUnless(NODE, "node is not installed")
class ParseTests(unittest.TestCase):
    LRC = ("[ar:Someone]\n[ti:A song]\n[offset:+250]\n"
           "[00:12.50] First line\n[00:20.00]Second line\n"
           "[00:30.5][01:10.25] Chorus\n[01:00.00]\n[01:05]<01:05.10> word <01:05.40> by word\n")

    def test_stamped_lines_in_time_order_and_tags_dropped(self):
        lines = run_js(f"parseLrc({json.dumps(self.LRC)})")
        self.assertEqual([(l["time"], l["text"]) for l in lines], [
            (12.5, "First line"), (20.0, "Second line"), (30.5, "Chorus"), (60.0, ""),
            (65.0, "word by word"), (70.25, "Chorus")])

    def test_two_stamps_on_one_line_repeat_it(self):
        lines = run_js('parseLrc("[00:30.5][01:10.25] Chorus")')
        self.assertEqual([l["time"] for l in lines], [30.5, 70.25])

    def test_fractions_of_any_length(self):
        self.assertEqual([l["time"] for l in run_js('parseLrc("[00:01.5]a\\n[00:02.05]b\\n[00:03.125]c\\n[00:04]d")')],
                         [1.5, 2.05, 3.125, 4.0])

    def test_nothing_parses_to_nothing(self):
        for text in ("", "no stamps here", "[ar:x]"):
            self.assertEqual(run_js(f"parseLrc({json.dumps(text)})"), [])
        self.assertEqual(run_js("parseLrc(null)"), [])

    def test_the_current_line_is_the_last_that_has_started(self):
        lines = "[{time:10,text:'a'},{time:20,text:'b'},{time:30,text:'c'}]"
        cases = {0: -1, 9.99: -1, 10: 0, 19.9: 0, 20: 1, 29.99: 1, 30: 2, 999: 2}
        for position, expected in cases.items():
            self.assertEqual(run_js(f"indexAt({lines}, {position})"), expected, position)
        self.assertEqual(run_js("indexAt([], 5)"), -1)

    def test_what_lrclib_answered(self):
        synced = run_js("""interpret('{"syncedLyrics": "[00:01.00] hi", "plainLyrics": "hi"}')""")
        self.assertEqual((synced["state"], len(synced["lines"])), ("synced", 1))
        plain = run_js("""interpret('{"syncedLyrics": null, "plainLyrics": "just words"}')""")
        self.assertEqual((plain["state"], plain["plain"]), ("plain", "just words"))
        for output in ("", "  ", "not json", "{}", '{"syncedLyrics": "", "plainLyrics": ""}', "null", "[]", "42"):
            self.assertEqual(run_js(f"interpret({json.dumps(output)})")["state"], "none", output)

    def test_a_search_answer_uses_the_first_result_with_timing(self):
        answer = json.dumps([{"plainLyrics": "a"}, {"syncedLyrics": "[00:05.00] second", "plainLyrics": "b"},
                             {"syncedLyrics": "[00:06.00] third"}])
        result = run_js(f"interpret({json.dumps(answer)})")
        self.assertEqual((result["state"], [l["text"] for l in result["lines"]]), ("synced", ["second"]))
        # no result has timing: the first one's plain words
        untimed = json.dumps([{"plainLyrics": "first words"}, {"plainLyrics": "other"}])
        self.assertEqual(run_js(f"interpret({json.dumps(untimed)})")["plain"], "first words")


class WiringTests(unittest.TestCase):
    def read(self, path):
        return (II / path).read_text(encoding="utf-8")

    def test_the_widget_is_loaded_configured_and_in_settings(self):
        self.assertIn("LyricsWidget {", self.read("modules/ii/background/Background.qml"))
        config = self.read("modules/common/Config.qml")
        self.assertRegex(config, r"property JsonObject lyrics: JsonObject \{\s+property bool enable: false")
        settings = self.read("modules/settings/BackgroundConfig.qml")
        self.assertIn("Config.options.background.widgets.lyrics.enable", settings)

    def test_the_network_is_asked_only_for_the_song_and_only_while_a_widget_is_there(self):
        service = self.read("services/Lyrics.qml")
        self.assertIn("if (users <= 0 || key === \"\")", service)
        self.assertIn("https://lrclib.net/api/get", service)
        self.assertNotIn("jq", service, "curl is the only tool it needs")
        # The words of the song go as arguments to curl, never into the shell's own text.
        self.assertIn('"_", artist, title', service)
        self.assertNotIn("${artist}", service)
        widget = self.read("modules/ii/background/widgets/lyrics/LyricsWidget.qml")
        self.assertIn("Component.onCompleted: Lyrics.users++", widget)
        self.assertIn("Component.onDestruction: Lyrics.users--", widget)


if __name__ == "__main__":
    unittest.main()
