"""JSON-with-comments, the format Waybar actually uses."""

from __future__ import annotations

import unittest

from halcyon import jsonc


class TestStrip(unittest.TestCase):
    def test_line_comments(self) -> None:
        self.assertEqual(jsonc.loads('{"a": 1} // trailing'), {"a": 1})
        self.assertEqual(jsonc.loads('// leading\n{"a": 1}'), {"a": 1})

    def test_block_comments(self) -> None:
        self.assertEqual(jsonc.loads('{/* why */ "a": 1}'), {"a": 1})
        self.assertEqual(jsonc.loads('{"a": /* 2 */ 1}'), {"a": 1})

    def test_comment_markers_inside_strings_survive(self) -> None:
        # A format string like "{icon} // {text}" is not a comment, and a
        # naive stripper eats it.
        self.assertEqual(
            jsonc.loads('{"url": "https://example.com/x"}'),
            {"url": "https://example.com/x"},
        )
        self.assertEqual(jsonc.loads('{"f": "a // b"}'), {"f": "a // b"})
        self.assertEqual(jsonc.loads('{"f": "a /* b */ c"}'), {"f": "a /* b */ c"})

    def test_escaped_quotes_do_not_end_the_string(self) -> None:
        self.assertEqual(jsonc.loads(r'{"f": "a\" // b"}'), {"f": 'a" // b'})
        self.assertEqual(jsonc.loads(r'{"f": "back\\"} // c'), {"f": "back\\"})

    def test_trailing_commas(self) -> None:
        self.assertEqual(jsonc.loads('{"a": 1,}'), {"a": 1})
        self.assertEqual(jsonc.loads("[1, 2, 3,]"), [1, 2, 3])
        self.assertEqual(jsonc.loads('{"a": [1,],}'), {"a": [1]})

    def test_commas_inside_strings_are_left_alone(self) -> None:
        self.assertEqual(jsonc.loads('{"f": "a,}"}'), {"f": "a,}"})

    def test_a_realistic_waybar_fragment(self) -> None:
        text = """
        {
            // The bar itself
            "layer": "top",
            "modules-right": [
                "pulseaudio",   // volume
                "battery",
            ],
            /* Format strings keep their slashes */
            "clock": { "format": "{:%H:%M}" },
        }
        """
        parsed = jsonc.loads(text)
        self.assertEqual(parsed["layer"], "top")
        self.assertEqual(parsed["modules-right"], ["pulseaudio", "battery"])
        self.assertEqual(parsed["clock"]["format"], "{:%H:%M}")

    def test_invalid_json_still_raises(self) -> None:
        import json

        with self.assertRaises(json.JSONDecodeError):
            jsonc.loads('{"a": }')


if __name__ == "__main__":
    unittest.main()
