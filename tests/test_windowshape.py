"""The Firefox window shape: a setting that holds Firefox to 3:2."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
import warnings

from halcyon import pipeline, render, settings as settings_module, windowshape

from .helpers import IsolatedHalcyon

SURFACE = windowshape.PRESETS["surface-pro-5"]

#: Monitors of every proportion the rule has to cope with.
MONITORS = [
    (1920, 1080),  # 16:9
    (2560, 1440),
    (3840, 2160),
    (2736, 1824),  # a Surface Pro 5's own 3:2 panel
    (1366, 768),  # small laptop
    (1080, 1920),  # portrait
    (3440, 1440),  # ultrawide
    (1024, 1024),  # square
]


def evaluate(expression: str, monitor_w: int, monitor_h: int) -> float:
    """Evaluate a size expression the way Hyprland's muParser would.

    The syntax we emit — `min(a,b)`, `*`, `/` and two variables — means
    the same in Python, which is the only reason this is safe. It is
    checked against a real muParser separately; this keeps the guarantee
    in the test suite for machines that do not have one.
    """
    return float(
        eval(  # noqa: S307 — our own generated arithmetic, no builtins
            expression,
            {"__builtins__": {}},
            {"min": min, "monitor_w": monitor_w, "monitor_h": monitor_h},
        )
    )


class TestPresets(unittest.TestCase):
    def test_the_surface_pro_5_is_three_by_two(self) -> None:
        self.assertEqual((SURFACE.width, SURFACE.height), (3, 2))

    def test_that_really_is_what_2736_by_1824_reduces_to(self) -> None:
        # The claim in the preset's description, checked rather than
        # trusted.
        import math

        divisor = math.gcd(2736, 1824)
        self.assertEqual((2736 // divisor, 1824 // divisor), (3, 2))
        self.assertAlmostEqual(2736 / 1824, SURFACE.ratio)

    def test_off_is_always_an_option_and_listed_first(self) -> None:
        self.assertEqual(windowshape.choices()[0], windowshape.OFF)
        self.assertIn("surface-pro-5", windowshape.choices())

    def test_every_preset_has_a_description(self) -> None:
        for name, shape in windowshape.PRESETS.items():
            self.assertTrue(shape.description, msg=name)

    def test_resolve(self) -> None:
        self.assertEqual(windowshape.resolve("surface-pro-5"), SURFACE)
        self.assertEqual(windowshape.resolve(" Surface-Pro-5 "), SURFACE)
        for nothing in ("off", "", "banana", None, 3, ["surface-pro-5"]):
            self.assertIsNone(windowshape.resolve(nothing), msg=repr(nothing))

    def test_is_known_separates_off_from_garbage(self) -> None:
        self.assertTrue(windowshape.is_known("off"))
        self.assertTrue(windowshape.is_known("surface-pro-5"))
        self.assertFalse(windowshape.is_known("banana"))
        self.assertFalse(windowshape.is_known(None))


class TestSizeExpression(unittest.TestCase):
    def setUp(self) -> None:
        self.expression = windowshape.size_expression(SURFACE)
        self.width, self.height = self.expression.split(" ")

    def test_exactly_one_space_separates_the_two_axes(self) -> None:
        # Hyprland's parseExpressionVec2 splits on the *first*
        # whitespace. A space inside either axis, such as after a comma,
        # would hand it half an expression and silently break the rule.
        self.assertEqual(self.expression.count(" "), 1)
        self.assertFalse(any(ch.isspace() for ch in self.width + self.height))

    def test_the_ratio_is_exactly_three_to_two_on_every_monitor(self) -> None:
        for monitor_w, monitor_h in MONITORS:
            w = evaluate(self.width, monitor_w, monitor_h)
            h = evaluate(self.height, monitor_w, monitor_h)
            self.assertAlmostEqual(
                w / h, 1.5, places=9, msg=f"{monitor_w}x{monitor_h}"
            )

    def test_the_window_always_fits_the_monitor(self) -> None:
        for monitor_w, monitor_h in MONITORS:
            w = evaluate(self.width, monitor_w, monitor_h)
            h = evaluate(self.height, monitor_w, monitor_h)
            self.assertLessEqual(w, monitor_w * windowshape.FILL + 1e-9)
            self.assertLessEqual(h, monitor_h * windowshape.FILL + 1e-9)

    def test_and_is_as_large_as_that_allows(self) -> None:
        # Fitting is easy — a 1px window fits. The point is that it uses
        # the room: one axis reaches the limit.
        for monitor_w, monitor_h in MONITORS:
            w = evaluate(self.width, monitor_w, monitor_h)
            h = evaluate(self.height, monitor_w, monitor_h)
            limit_w = monitor_w * windowshape.FILL
            limit_h = monitor_h * windowshape.FILL
            touches = abs(w - limit_w) < 1e-6 or abs(h - limit_h) < 1e-6
            self.assertTrue(touches, msg=f"{monitor_w}x{monitor_h}: {w}x{h}")

    def test_a_portrait_monitor_gets_a_landscape_window_that_fits_its_width(self) -> None:
        w = evaluate(self.width, 1080, 1920)
        h = evaluate(self.height, 1080, 1920)
        self.assertGreater(w, h)
        self.assertLessEqual(w, 1080 * windowshape.FILL + 1e-9)

    def test_a_different_shape_gets_its_own_ratio(self) -> None:
        wide = windowshape.Shape(16, 9, "test")
        width, height = windowshape.size_expression(wide).split(" ")
        for monitor_w, monitor_h in MONITORS:
            ratio = evaluate(width, monitor_w, monitor_h) / evaluate(
                height, monitor_w, monitor_h
            )
            self.assertAlmostEqual(ratio, 16 / 9, places=9)

    def test_no_exponent_notation_leaks_into_the_expression(self) -> None:
        # `1e-05` is valid in Python and not what muParser wants to see.
        small = windowshape.size_expression(SURFACE, fill=0.00001)
        self.assertNotIn("e-", small)
        self.assertIn("0.00001", small)

    def test_numbers_are_trimmed_but_not_mangled(self) -> None:
        self.assertEqual(windowshape._number(0.85), "0.85")
        self.assertEqual(windowshape._number(1.0), "1")
        self.assertEqual(windowshape._number(0.5), "0.5")

    def test_a_nonsense_fill_is_refused(self) -> None:
        for bad in (0, -0.5, 1.01, 2):
            with self.assertRaises(ValueError, msg=str(bad)):
                windowshape.size_expression(SURFACE, fill=bad)

    def test_a_full_screen_fill_is_allowed(self) -> None:
        width, height = windowshape.size_expression(SURFACE, fill=1.0).split(" ")
        self.assertAlmostEqual(evaluate(width, 3000, 2000) / evaluate(height, 3000, 2000), 1.5)


class TestSettingValidation(IsolatedHalcyon):
    PATH = "applications.firefox.aspectRatio"

    def test_it_defaults_to_off(self) -> None:
        self.assertEqual(settings_module.get(self.PATH), "off")

    def test_a_valid_value_is_stored(self) -> None:
        settings_module.set_value(self.PATH, "surface-pro-5")
        self.assertEqual(settings_module.get(self.PATH), "surface-pro-5")

    def test_a_typo_is_refused_and_names_what_was_meant(self) -> None:
        with self.assertRaises(settings_module.SettingsError) as raised:
            settings_module.set_value(self.PATH, "surface-pro")
        message = str(raised.exception)
        self.assertIn("surface-pro-5", message)
        self.assertIn("off", message)

    def test_a_refused_value_changes_nothing(self) -> None:
        settings_module.set_value(self.PATH, "surface-pro-5")
        with self.assertRaises(settings_module.SettingsError):
            settings_module.set_value(self.PATH, "banana")
        self.assertEqual(settings_module.get(self.PATH), "surface-pro-5")

    def test_the_declared_choices_are_the_ones_the_code_understands(self) -> None:
        self.assertEqual(
            settings_module.choices_for(self.PATH), windowshape.choices()
        )

    def test_a_free_form_setting_has_no_choices(self) -> None:
        self.assertIsNone(settings_module.choices_for("applications.terminal"))

    def test_off_is_accepted_again_after_enabling(self) -> None:
        settings_module.set_value(self.PATH, "surface-pro-5")
        settings_module.set_value(self.PATH, "off")
        self.assertEqual(settings_module.get(self.PATH), "off")


class TestWindowRule(unittest.TestCase):
    def build(self, value: object):
        settings, tokens = pipeline.build(settings_module.defaults())
        settings["applications"]["firefox"]["aspectRatio"] = value
        return settings, tokens

    def runtime(self, value: object) -> str:
        settings, tokens = self.build(value)
        return render.render_hypr_runtime_lua(settings, tokens, {})

    def test_nothing_is_emitted_by_default(self) -> None:
        self.assertNotIn("halcyon-firefox-aspect-ratio", self.runtime("off"))

    def test_the_rule_is_emitted_when_enabled(self) -> None:
        text = self.runtime("surface-pro-5")
        self.assertIn("halcyon-firefox-aspect-ratio", text)

    def test_the_rule_floats_sizes_and_keeps_the_ratio(self) -> None:
        settings, _ = self.build("surface-pro-5")
        rule = render._firefox_shape_rule(settings)
        assert rule is not None
        # float: a tiled window cannot hold a shape. size: sets it on
        # open. keep_aspect_ratio: holds it through a mouse resize.
        self.assertIs(rule["float"], True)
        self.assertIs(rule["center"], True)
        self.assertIs(rule["keep_aspect_ratio"], True)
        self.assertEqual(rule["size"], windowshape.size_expression(SURFACE))

    def test_it_matches_firefox_and_only_firefox(self) -> None:
        import re

        settings, _ = self.build("surface-pro-5")
        rule = render._firefox_shape_rule(settings)
        assert rule is not None
        pattern = re.compile(rule["match"]["class"])
        for firefox in ("firefox", "org.mozilla.firefox", "firefox-esr"):
            self.assertTrue(pattern.match(firefox), msg=firefox)
        for other in ("kitty", "chromium", "firefoxy", "librewolf", "zen", ""):
            self.assertFalse(pattern.match(other), msg=other)

    def test_it_comes_before_the_rules_that_must_override_it(self) -> None:
        # Firefox's Picture-in-Picture window has the same class as the
        # browser. Hyprland applies rules in order and a later size or
        # move wins, so this rule must come first or PiP is resized to
        # 3:2 instead of keeping its own small, pinned shape.
        text = self.runtime("surface-pro-5")
        shape = text.index("halcyon-firefox-aspect-ratio")
        for later in (
            "halcyon-picture-in-picture",
            "halcyon-float-dialogs",
            "halcyon-float-pickers",
            "halcyon-float-calculator",
        ):
            self.assertLess(shape, text.index(later), msg=later)

    def test_an_unknown_value_is_ignored_with_a_warning_not_an_error(self) -> None:
        # `set` refuses it, so it can only come from a hand-edited file —
        # and a cosmetic preference must not stop the desktop generating.
        settings, _ = self.build("banana")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            rule = render._firefox_shape_rule(settings)
        self.assertIsNone(rule)
        self.assertTrue(any("banana" in str(w.message) for w in caught))

    def test_off_does_not_warn(self) -> None:
        settings, _ = self.build("off")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            render._firefox_shape_rule(settings)
        self.assertEqual(caught, [])

    def test_a_missing_subtree_is_treated_as_off(self) -> None:
        # An older settings document with no `firefox` key at all.
        self.assertIsNone(render._firefox_shape_rule({"applications": {}}))
        self.assertIsNone(render._firefox_shape_rule({}))

    def test_the_generated_lua_parses(self) -> None:
        compiler = next(
            (c for c in ("luac5.4", "luac") if shutil.which(c)), None
        )
        if compiler is None:
            self.skipTest("no Lua compiler available")
        with tempfile.NamedTemporaryFile("w", suffix=".lua", delete=False) as handle:
            handle.write(self.runtime("surface-pro-5"))
            path = handle.name
        try:
            done = subprocess.run(
                [compiler, "-p", path], capture_output=True, text=True
            )
            self.assertEqual(done.returncode, 0, msg=done.stderr)
        finally:
            os.unlink(path)

    def test_the_default_settings_document_has_the_key(self) -> None:
        defaults = settings_module.defaults()
        self.assertEqual(defaults["applications"]["firefox"]["aspectRatio"], "off")
        json.dumps(defaults)


if __name__ == "__main__":
    unittest.main()
