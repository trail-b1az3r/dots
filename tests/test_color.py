"""Colour maths: the parts that must be exactly right."""

from __future__ import annotations

import unittest

from halcyon import color


def hue_delta(a: float, b: float) -> float:
    """Shortest angular distance between two hues, in degrees."""
    return abs((a - b + 180.0) % 360.0 - 180.0)


class TestParsing(unittest.TestCase):
    def test_hex_forms(self) -> None:
        self.assertEqual(color.to_hex(color.parse_hex("#0A84FF")), "#0a84ff")
        self.assertEqual(color.to_hex(color.parse_hex("0A84FF")), "#0a84ff")
        self.assertEqual(color.to_hex(color.parse_hex("#08f")), "#0088ff")
        # Alpha is accepted and discarded rather than rejected.
        self.assertEqual(color.to_hex(color.parse_hex("#0a84ff80")), "#0a84ff")

    def test_rejects_nonsense(self) -> None:
        for value in ("", "blue", "#12345", "#gggggg"):
            with self.assertRaises(ValueError):
                color.parse_hex(value)

    def test_output_formats(self) -> None:
        blue = color.parse_hex("#0a84ff")
        # Hyprland wants RRGGBBAA; QML wants #AARRGGBB. Getting these two
        # the wrong way round produces plausible-looking wrong colours.
        self.assertEqual(color.to_hypr(blue, 1.0), "rgba(0a84ffff)")
        self.assertEqual(color.to_argb_hex(blue, 1.0), "#ff0a84ff")
        self.assertEqual(color.to_argb_hex(blue, 0.0), "#000a84ff")


class TestOklab(unittest.TestCase):
    def test_round_trip(self) -> None:
        for value in ("#0a84ff", "#ffffff", "#000000", "#7f3d2a", "#3ecf8e"):
            original = color.parse_hex(value)
            result = color.oklab_to_rgb(color.rgb_to_oklab(original))
            for a, b in zip(original, result):
                self.assertAlmostEqual(a, b, places=4, msg=value)

    def test_lightness_is_monotonic(self) -> None:
        base = color.parse_hex("#0a84ff")
        previous = -1.0
        for target in (0.1, 0.3, 0.5, 0.7, 0.9):
            lightness = color.lightness(color.with_lightness(base, target))
            self.assertGreater(lightness, previous)
            previous = lightness

    def test_hue_survives_lightness_changes(self) -> None:
        # A saturated blue at these lightnesses falls outside sRGB. Chroma
        # reduction keeps the hue; per-channel clipping would not, and this
        # is the test that caught it doing so. What is left is 8-bit
        # rounding, which bites hardest near black.
        base = color.parse_hex("#0a84ff")
        original_hue = color.rgb_to_oklch(base)[2]
        for target in (0.1, 0.3, 0.5, 0.8, 0.95):
            hue = color.rgb_to_oklch(color.with_lightness(base, target))[2]
            self.assertLessEqual(hue_delta(hue, original_hue), 1.5, msg=str(target))

    def test_out_of_gamut_colours_keep_their_lightness(self) -> None:
        for value in ("#0a84ff", "#3ecf8e", "#f5af20"):
            base = color.parse_hex(value)
            _, chroma, hue = color.rgb_to_oklch(base)
            # Ask for far more chroma than sRGB can hold at this lightness.
            forced = color.oklch_to_rgb((0.75, chroma * 3.0, hue))
            self.assertAlmostEqual(color.lightness(forced), 0.75, places=2, msg=value)


class TestContrast(unittest.TestCase):
    def test_known_ratios(self) -> None:
        white = color.parse_hex("#ffffff")
        black = color.parse_hex("#000000")
        self.assertAlmostEqual(color.contrast_ratio(white, black), 21.0, places=1)
        self.assertAlmostEqual(color.contrast_ratio(white, white), 1.0, places=3)

    def test_readable_on_meets_the_target(self) -> None:
        for background in ("#0b0d10", "#ffffff", "#0a84ff", "#7f3d2a", "#f5af20"):
            rgb = color.parse_hex(background)
            foreground = color.readable_on(rgb, target=4.5)
            self.assertGreaterEqual(
                color.contrast_ratio(foreground, rgb), 4.5, msg=background
            )

    def test_ensure_contrast_keeps_hue_where_it_can(self) -> None:
        background = color.parse_hex("#0b0d10")
        accent = color.parse_hex("#0a4a80")
        fixed = color.ensure_contrast(accent, background, 4.5)
        self.assertGreaterEqual(color.contrast_ratio(fixed, background), 4.5)
        # The hue should survive the lightness change.
        self.assertLessEqual(
            hue_delta(color.rgb_to_oklch(fixed)[2], color.rgb_to_oklch(accent)[2]),
            1.5,
        )

    def test_ensure_contrast_leaves_good_colours_alone(self) -> None:
        background = color.parse_hex("#0b0d10")
        accent = color.parse_hex("#ffffff")
        self.assertEqual(color.ensure_contrast(accent, background, 4.5), accent)


class TestMixing(unittest.TestCase):
    def test_endpoints(self) -> None:
        a = color.parse_hex("#000000")
        b = color.parse_hex("#ffffff")
        self.assertEqual(color.to_hex(color.mix(a, b, 0.0)), "#000000")
        self.assertEqual(color.to_hex(color.mix(a, b, 1.0)), "#ffffff")

    def test_clamps_out_of_range(self) -> None:
        a = color.parse_hex("#000000")
        b = color.parse_hex("#ffffff")
        self.assertEqual(color.to_hex(color.mix(a, b, -5)), "#000000")
        self.assertEqual(color.to_hex(color.mix(a, b, 5)), "#ffffff")


if __name__ == "__main__":
    unittest.main()
