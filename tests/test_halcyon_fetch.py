"""The Halcyon mark in 3D, and `halcyon-theme fetch`."""

from __future__ import annotations

import io
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dots", ".config", "hypr", "hyprland", "halcyon"))

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

    def test_the_mark_has_both_a_sword_and_a_trident(self) -> None:
        # The sword is left of centre and the trident right of it.
        xs = [v[0] for tri in logo3d.MODEL for v in tri[:3]]
        left = [x for x in xs if x < 0]
        right = [x for x in xs if x > 0.1]
        self.assertTrue(left and right)


class TestRendering(unittest.TestCase):
    def test_every_frame_has_the_requested_shape(self) -> None:
        for step in range(24):
            frame = logo3d.render_frame(step * math.pi / 12, cols=34, rows=18)
            self.assertEqual(len(frame), 18)
            for line in frame:
                self.assertLessEqual(len(line), 34)
                for char in line:
                    self.assertTrue(char == " " or char in logo3d.RAMP, repr(char))

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

    def test_spin_redraws_in_place_and_restores_the_cursor(self) -> None:
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
        self.assertIn("\x1b[18A", text, "frames after the first should move back up")

    def test_reduced_motion_or_no_terminal_prints_once(self) -> None:
        out = io.StringIO()  # not a terminal
        status = fetch.run(spin_seconds=2.0, as_json_out=False, out=out)
        self.assertEqual(status, 0)
        self.assertNotIn("\x1b[?25l", out.getvalue())


if __name__ == "__main__":
    unittest.main()
