"""The Halcyon mark in 3D, and `halcyon-theme fetch`."""

from __future__ import annotations

import io
import math
import os
import sys
import time
import unittest
import unittest.mock

TOOL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dots", ".config", "hypr", "hyprland", "halcyon"))
sys.path.insert(0, TOOL_DIR)

import fetch_mark as logo3d  # noqa: E402
import halcyon_fetch as fetch  # noqa: E402


def _area(poly: list[tuple[float, float]]) -> float:
    total = 0.0
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % len(poly)]
        total += x1 * y2 - x2 * y1
    return abs(total) / 2.0


class TestTriangulation(unittest.TestCase):
    def test_every_outline_is_covered_exactly_by_its_triangles(self) -> None:
        # Ear clipping has to reproduce the polygon's area, including for
        # the concave fork, where a naive fan would spill outside it.
        for outline, _half in logo3d.SOLIDS:
            pts = [(float(x), float(y)) for x, y in outline]
            triangles = logo3d.triangulate(pts)
            self.assertEqual(len(triangles), len(pts) - 2)
            covered = sum(
                _area([pts[i] for i in tri]) for tri in triangles
            )
            self.assertAlmostEqual(covered, _area(pts), places=6)

    def test_winding_does_not_change_the_result(self) -> None:
        pts = [(float(x), float(y)) for x, y in logo3d._FORK]
        forward = logo3d.triangulate(pts)
        backward = logo3d.triangulate(list(reversed(pts)))
        self.assertEqual(len(forward), len(backward))

    def test_fewer_than_three_corners_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            logo3d.triangulate([(0.0, 0.0), (1.0, 0.0)])


class TestModel(unittest.TestCase):
    def test_front_and_back_faces_match_for_every_solid(self) -> None:
        fronts = sum(1 for *_, n in logo3d.MODEL if n == (0.0, 0.0, 1.0))
        backs = sum(1 for *_, n in logo3d.MODEL if n == (0.0, 0.0, -1.0))
        self.assertEqual(fronts, backs)
        self.assertGreater(fronts, 0)

    def test_side_normals_lie_in_the_plane(self) -> None:
        for *_, normal in logo3d.MODEL:
            if normal not in ((0.0, 0.0, 1.0), (0.0, 0.0, -1.0)):
                self.assertAlmostEqual(normal[2], 0.0)
                self.assertAlmostEqual(math.hypot(normal[0], normal[1]), 1.0, places=6)

    def test_the_mark_comes_from_the_logo_outlines(self) -> None:
        # The solids are the traced logo, so the model is one non-empty set of
        # triangles that lies inside the unit cube.
        self.assertGreater(len(logo3d.MODEL), 0)
        for tri in logo3d.MODEL:
            for vertex in tri[:3]:
                self.assertTrue(all(-1.0 <= value <= 1.0 for value in vertex), vertex)

    def test_the_outlines_file_is_what_the_model_uses(self) -> None:
        import json
        import pathlib
        data = json.loads((pathlib.Path(logo3d.__file__).with_name("mark_outline.json")).read_text())
        self.assertEqual(len(logo3d.SOLIDS), len(data["polygons"]))

    def test_the_mark_is_visible_at_every_angle(self) -> None:
        for step in range(24):
            frame = logo3d.render_frame(step * math.pi / 12)
            self.assertTrue(any(line.strip() for line in frame), step)

    def test_the_mark_is_recognisably_the_same_object_from_the_front_and_the_back(self) -> None:
        # Turning by a half revolution shows the other face of the same solid;
        # it must still fill about the same number of cells.
        def filled(frame: list[str]) -> int:
            return sum(1 for line in frame for ch in line if ch != " ")

        front = filled(logo3d.render_frame(0.0))
        back = filled(logo3d.render_frame(math.pi))
        self.assertLess(abs(front - back) / front, 0.1)

    def test_rendering_is_deterministic(self) -> None:
        self.assertEqual(logo3d.render_frame(0.7), logo3d.render_frame(0.7))

    def test_the_mark_turns_edge_on_at_a_quarter_turn(self) -> None:
        def filled(frame: list[str]) -> int:
            return sum(1 for line in frame for ch in line if ch != " ")

        self.assertLess(filled(logo3d.render_frame(math.pi / 2)), filled(logo3d.render_frame(0.0)))


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

    def test_compose_puts_the_mark_on_the_left_of_every_row(self) -> None:
        frame = ["**", "*"]
        info = ["one", "two", "three"]
        rows = fetch.compose(frame, info)
        self.assertEqual(len(rows), 3)
        for row in rows:
            self.assertTrue(row.startswith(("**", "* ", "  ")))
        self.assertTrue(rows[0].endswith("one") or "one" in rows[0])

    def test_static_output_has_no_escape_codes_without_colour(self) -> None:
        out = io.StringIO()
        fetch.print_static(
            [fetch.Field("OS", "Linux")], out, colour=False
        )
        self.assertNotIn("\x1b", out.getvalue())
        self.assertIn("OS", out.getvalue())

    def test_spin_loops_for_the_given_time_and_restores_the_cursor(self) -> None:
        out = io.StringIO()
        fetch.spin(
            [fetch.Field("OS", "Linux")],
            out,
            colour=False,
            seconds=0.3,
            sleep=lambda _s: None,
        )
        text = out.getvalue()
        self.assertTrue(text.startswith("\x1b[?25l"), "cursor should be hidden first")
        self.assertTrue(text.endswith("\x1b[?25h"), "cursor should be restored last")
        self.assertGreater(text.count("\x1b["), 3)
        self.assertIn(f"\x1b[{fetch.FRAME_ROWS}A", text, "frames after the first should move back up")

    def test_an_endless_spin_stops_cleanly_on_interrupt(self) -> None:
        out = io.StringIO()
        calls = {"n": 0}

        def interrupt_after_a_few(_seconds: float) -> None:
            calls["n"] += 1
            if calls["n"] >= 5:
                raise KeyboardInterrupt

        with self.assertRaises(KeyboardInterrupt):
            fetch.spin([fetch.Field("OS", "Linux")], out, colour=False, seconds=None,
                       sleep=interrupt_after_a_few)
        text = out.getvalue()
        self.assertGreaterEqual(text.count(f"\x1b[{fetch.FRAME_ROWS}A"), 3, "the frame should redraw in place")
        self.assertTrue(text.endswith("\x1b[?25h"), "the cursor should be restored on interrupt")

    def test_a_key_settles_the_mark_at_once(self) -> None:
        out = io.StringIO()
        calls = []

        def key_pressed(timeout: float) -> bool:
            calls.append(timeout)
            return len(calls) == 3

        fetch.spin([fetch.Field("OS", "Linux")], out, colour=False, seconds=60.0, key_pressed=key_pressed)
        text = out.getvalue()
        self.assertEqual(len(calls), 3, "it stops at the frame the key came in, not after 60 seconds")
        settled = fetch.compose(logo3d.render_frame(fetch.SETTLED_YAW, cols=fetch.FRAME_COLS,
                                                    rows=fetch.FRAME_ROWS), fetch.info_lines([fetch.Field("OS", "Linux")], colour=False))
        last = text.rsplit(f"\x1b[{fetch.FRAME_ROWS}A\r", 1)[-1]
        self.assertTrue(last.startswith(settled[0] + "\x1b[K"), "the last frame is the settled one")
        self.assertTrue(text.endswith("\x1b[?25h"))

    def test_on_a_terminal_a_key_stops_it_and_is_left_for_the_shell(self) -> None:
        # A new terminal: the fetch turns for 3 s, someone starts typing. It must stop at once, and the key
        # must still be there for the shell's prompt to read.
        import pty
        import select
        child = (
            "import sys, os, time, termios; sys.path.insert(0, %r)\n"
            "import halcyon_fetch as f\n"
            "f.collect = lambda: [f.Field('OS', 'Linux')]\n"
            "start = time.monotonic(); f.run(spin_seconds=3.0, as_json_out=False)\n"
            "took = time.monotonic() - start\n"
            "mode = termios.tcgetattr(0)\n"
            "mode[3] &= ~termios.ICANON; mode[6][termios.VMIN] = 0; mode[6][termios.VTIME] = 5\n"
            "termios.tcsetattr(0, termios.TCSANOW, mode)\n"
            "sys.stdout.write('TOOK %%.2f LEFT %%r\\n' %% (took, os.read(0, 16))); sys.stdout.flush()\n"
        ) % str(TOOL_DIR)
        pid, fd = pty.fork()
        if pid == 0:
            os.execvp(sys.executable, [sys.executable, "-c", child])
        output = b""
        time.sleep(0.6)
        os.write(fd, b"l")
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            ready, _, _ = select.select([fd], [], [], 0.2)
            if not ready:
                continue
            try:
                chunk = os.read(fd, 65536)
            except OSError:
                break
            if not chunk:
                break
            output += chunk
            if b"LEFT" in output and output.rstrip().endswith((b")", b"'")):
                break
        os.waitpid(pid, 0)
        tail = output.decode(errors="replace").split("TOOK", 1)
        self.assertEqual(len(tail), 2, output[-400:])
        took = float(tail[1].split()[0])
        self.assertLess(took, 1.5, "the spin stops when a key comes, not after 3 s")
        self.assertIn("LEFT b'l'", tail[1], "the key is left queued for the shell")

    def test_reduced_motion_or_no_terminal_prints_once(self) -> None:
        out = io.StringIO()  # not a terminal
        status = fetch.run(spin_seconds=2.0, as_json_out=False, out=out)
        self.assertEqual(status, 0)
        self.assertNotIn("\x1b[?25l", out.getvalue())


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
