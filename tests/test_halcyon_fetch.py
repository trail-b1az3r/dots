"""`halcyon-theme fetch`: the summary of this machine, as text or JSON, and fastfetch's text."""

from __future__ import annotations

import io
import json
import os
import sys
import unittest
import unittest.mock

TOOL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dots", ".config", "hypr", "hyprland", "halcyon"))
sys.path.insert(0, TOOL_DIR)

import halcyon_fetch as fetch  # noqa: E402


class TestFetch(unittest.TestCase):
    def test_uptime_reads_naturally(self) -> None:
        self.assertEqual(fetch.format_uptime(11 * 60), "11 min")
        self.assertEqual(fetch.format_uptime(3 * 3600 + 5 * 60), "3 hours, 5 min")
        self.assertEqual(fetch.format_uptime(86400 + 3600), "1 day, 1 hour, 0 min")

    def test_json_keys_every_line_even_without_a_label(self) -> None:
        fields = [fetch.Field("", "me@box"), fetch.Field("OS", "Linux"), fetch.Field("", "tail")]
        data = fetch.as_json(fields)
        self.assertEqual(data["user"], "me@box")
        self.assertEqual(data["OS"], "Linux")
        self.assertIn("line2", data)

    def test_collect_always_reports_the_user(self) -> None:
        labels = {field.label: field.value for field in fetch.collect()}
        self.assertIn("Halcyon", labels)
        self.assertEqual(fetch.collect()[0].value.count("@"), 1)

    def test_text_output_has_no_escape_codes_without_colour(self) -> None:
        out = io.StringIO()
        fetch.print_text([fetch.Field("OS", "Linux")], out, colour=False)
        self.assertNotIn("\x1b", out.getvalue())
        self.assertIn("OS", out.getvalue())

    def test_run_prints_the_summary_once_and_no_motion(self) -> None:
        out = io.StringIO()
        self.assertEqual(fetch.run(as_json_out=False, out=out), 0)
        self.assertNotIn("\x1b[?25l", out.getvalue())
        self.assertIn("Halcyon", out.getvalue())

    def test_json_output_is_the_fields_as_an_object(self) -> None:
        out = io.StringIO()
        fetch.run(as_json_out=True, out=out)
        self.assertIsInstance(json.loads(out.getvalue()), dict)


class TestFastfetchSource(unittest.TestCase):
    def test_a_missing_fastfetch_gives_no_text(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as empty, \
             unittest.mock.patch.dict(os.environ, {"PATH": empty}):
            self.assertIsNone(fetch.fastfetch_lines())

    def test_fastfetch_output_is_stripped_of_colour_and_blank_lines(self) -> None:
        import stat
        import tempfile
        with tempfile.TemporaryDirectory() as bindir:
            script = os.path.join(bindir, "fastfetch")
            with open(script, "w", encoding="utf-8") as handle:
                handle.write("#!/bin/sh\n"
                             "printf '\\033[1;34mOS\\033[0m  Linux\\n\\n'\n"
                             "printf 'Kernel  6.1\\n'\n")
            os.chmod(script, os.stat(script).st_mode | stat.S_IEXEC)
            with unittest.mock.patch.dict(os.environ, {"PATH": bindir}):
                lines = fetch.fastfetch_lines()
        self.assertEqual(lines, ["OS  Linux", "Kernel  6.1"])

    def test_a_failing_fastfetch_falls_back(self) -> None:
        import stat
        import tempfile
        with tempfile.TemporaryDirectory() as bindir:
            script = os.path.join(bindir, "fastfetch")
            with open(script, "w", encoding="utf-8") as handle:
                handle.write("#!/bin/sh\nexit 3\n")
            os.chmod(script, os.stat(script).st_mode | stat.S_IEXEC)
            with unittest.mock.patch.dict(os.environ, {"PATH": bindir}):
                self.assertIsNone(fetch.fastfetch_lines())


if __name__ == "__main__":
    unittest.main()
