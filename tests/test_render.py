"""Generated configuration: the files Hyprland and Waybar actually read.

These run the real pipeline against the real defaults, because the value
of the generator is that its output parses — asserting on a mock would
prove nothing.
"""

from __future__ import annotations

import json
import os
import re
import unittest

from halcyon import hyprland, jsonc, render, theme
from halcyon import pipeline, settings as settings_module

from .helpers import IsolatedHalcyon


class TestLuaEncoding(unittest.TestCase):
    def test_strings_are_escaped(self) -> None:
        self.assertEqual(render.lua_string('say "hi"'), '"say \\"hi\\""')
        self.assertEqual(render.lua_string("a\\b"), '"a\\\\b"')
        self.assertEqual(render.lua_string("line\nbreak"), '"line\\nbreak"')

    def test_a_quote_cannot_escape_the_literal(self) -> None:
        # A font name or workspace label is user input; if it can close the
        # string it can append Lua.
        hostile = '"; os.execute("id"); x = "'
        encoded = render.lua_string(hostile)
        self.assertTrue(encoded.startswith('"') and encoded.endswith('"'))
        self.assertNotIn('"', encoded[1:-1].replace('\\"', ""))

    def test_scalars(self) -> None:
        self.assertEqual(render.lua_value(True), "true")
        self.assertEqual(render.lua_value(False), "false")
        self.assertEqual(render.lua_value(None), "nil")
        self.assertEqual(render.lua_value(3.0), "3")
        self.assertEqual(render.lua_value(3.5), "3.5")

    def test_tables(self) -> None:
        self.assertEqual(render.lua_value([]), "{}")
        self.assertEqual(render.lua_value({}), "{}")
        self.assertIn("gaps_in", render.lua_value({"gaps_in": 4}))
        # A key that is not an identifier has to be bracketed.
        self.assertIn('["a-b"]', render.lua_value({"a-b": 1}))

    def test_unsupported_types_are_refused(self) -> None:
        with self.assertRaises(TypeError):
            render.lua_value(object())


class TestGeneratedFiles(IsolatedHalcyon):
    @classmethod
    def setUpClass(cls) -> None:
        cls.settings, cls.tokens = pipeline.build(settings_module.defaults())
        cls.catalog = pipeline.load_catalog()
        cls.waybar_base = pipeline.load_waybar_modules()

    def test_tokens_are_json_serialisable(self) -> None:
        json.loads(render.render_theme_json(self.tokens))

    def test_hypr_theme_renders_a_lua_table(self) -> None:
        text = render.render_hypr_theme_lua(self.tokens, self.settings)
        self.assertIn("return {", text)
        self.assertIn("rounding", text)

    def test_the_runtime_config_is_checked_against_hyprlands_options(self) -> None:
        # render_hypr_runtime_lua raises rather than emit an unknown option
        # or an out-of-range number, so reaching this line is the check.
        text = render.render_hypr_runtime_lua(self.settings, self.tokens, {})
        self.assertIn("hl.config", text)

    def test_an_invented_option_is_refused(self) -> None:
        problems = hyprland.validate_options({"general": {"not_an_option": 1}})
        self.assertTrue(any("not_an_option" in p for p in problems))

    def test_an_out_of_range_value_is_refused(self) -> None:
        problems = hyprland.validate_options({"general": {"border_size": -5}})
        self.assertTrue(problems, "border_size = -5 should be out of range")

    def test_the_option_table_is_available_to_check_against(self) -> None:
        table, source = hyprland.options()
        self.assertTrue(table, "no option table: nothing would be validated")
        self.assertIn(source, ("hyprctl", "snapshot"))

    def test_animation_curves_are_monotonic_in_x(self) -> None:
        # A bezier whose x doubles back folds the curve on itself, and
        # Hyprland animates it wrong — a real bad curve got in this way.
        # Control points outside 0..1 in x are what cause it, so test the
        # property itself rather than the ordering of x1 and x2.
        for name, points in theme.CURVES.items():
            x1, _y1, x2, _y2 = points
            for value in (x1, x2):
                self.assertGreaterEqual(value, 0.0, msg=name)
                self.assertLessEqual(value, 1.0, msg=name)
            previous = -1.0
            for step in range(201):
                t = step / 200.0
                u = 1.0 - t
                x = 3 * u * u * t * x1 + 3 * u * t * t * x2 + t ** 3
                self.assertGreaterEqual(x, previous - 1e-12, msg=f"{name} at t={t}")
                previous = x

    def test_keybinds_have_no_duplicates(self) -> None:
        # render_hypr_keybinds_lua raises KeybindError on a collision.
        text = render.render_hypr_keybinds_lua(self.settings, self.catalog)
        self.assertIn("hl.bind", text)

    def test_a_deliberate_keybind_collision_is_dropped_and_explained(self) -> None:
        catalog = {
            "binds": [
                {
                    "id": "first",
                    "default": "SUPER + T",
                    "run": {"dsp": "hl.dsp.window.close()"},
                },
                {
                    "id": "second",
                    "default": "super + t",
                    "run": {"dsp": "hl.dsp.window.close()"},
                },
            ]
        }
        text = render.render_hypr_keybinds_lua(self.settings, catalog)
        # Hyprland would take the last binding silently; saying which one
        # lost, in the generated file, is how this stays debuggable.
        self.assertEqual(text.count('hl.bind("SUPER + T"'), 1)
        self.assertIn("skipped second", text)

    def test_the_catalog_cannot_smuggle_lua_through_a_dispatcher(self) -> None:
        catalog = {
            "binds": [
                {
                    "id": "evil",
                    "default": "SUPER + T",
                    "run": {"dsp": "os.execute('id')"},
                }
            ]
        }
        with self.assertRaises(render.KeybindError):
            render.render_hypr_keybinds_lua(self.settings, catalog)

    def test_an_action_less_bind_is_refused(self) -> None:
        catalog = {"binds": [{"id": "empty", "default": "SUPER + T", "run": {}}]}
        with self.assertRaises(render.KeybindError):
            render.render_hypr_keybinds_lua(self.settings, catalog)

    def test_waybar_config_is_valid_jsonc(self) -> None:
        text = render.render_waybar_config(self.settings, self.tokens, self.waybar_base)
        parsed = jsonc.loads(text)
        self.assertIn("layer", parsed)
        for side in ("modules-left", "modules-center", "modules-right"):
            self.assertIsInstance(parsed.get(side, []), list)

    def test_waybar_modules_all_have_a_definition(self) -> None:
        text = render.render_waybar_config(self.settings, self.tokens, self.waybar_base)
        parsed = jsonc.loads(text)
        listed = [
            name
            for side in ("modules-left", "modules-center", "modules-right")
            for name in parsed.get(side, [])
        ]
        for name in listed:
            # Waybar silently drops a module it has no config for, which
            # looks like a rendering bug rather than a config mistake.
            self.assertIn(name, parsed, msg=f"{name} is listed but not defined")

    def test_waybar_commands_use_an_absolute_halcyon_path(self) -> None:
        # Waybar runs these through /bin/sh with the PATH its systemd unit
        # inherited, which usually lacks ~/.local/bin. A bare `halcyon`
        # then fails silently: the button is there and does nothing.
        import os

        binary = os.path.join(self.root, "bin", "halcyon")
        os.makedirs(os.path.dirname(binary), exist_ok=True)
        with open(binary, "w", encoding="utf-8") as handle:
            handle.write("#!/bin/sh\nexit 0\n")
        os.chmod(binary, 0o755)

        config = dict(self.waybar_base)
        render._resolve_waybar_commands(config, binary)

        seen = 0
        for module in config.values():
            if not isinstance(module, dict):
                continue
            for field in render._WAYBAR_COMMAND_FIELDS:
                value = module.get(field)
                if not isinstance(value, str):
                    continue
                self.assertFalse(
                    value.startswith("halcyon "), msg=f"{field}: {value}"
                )
                if binary in value:
                    seen += 1
        self.assertGreater(seen, 0, "no command was rewritten")

    def test_waybar_commands_are_left_alone_when_no_binary_is_found(self) -> None:
        # Baking in a path that does not exist would be worse than a bare
        # name that at least works for anyone with ~/.local/bin on PATH.
        config = dict(self.waybar_base)
        render._resolve_waybar_commands(config, "halcyon")
        self.assertEqual(config["custom/menu"], self.waybar_base["custom/menu"])

    def test_only_halcyon_commands_are_rewritten(self) -> None:
        config = {
            "custom/x": {
                "on-click": "halcyon shell spotlight toggle",
                "on-click-right": "halcyonade --not-ours",
                "exec": "/usr/bin/true",
                "format": "halcyon is not a command here",
            }
        }
        render._resolve_waybar_commands(config, "/opt/bin/halcyon")
        module = config["custom/x"]
        self.assertEqual(module["on-click"], "/opt/bin/halcyon shell spotlight toggle")
        self.assertEqual(module["on-click-right"], "halcyonade --not-ours")
        self.assertEqual(module["exec"], "/usr/bin/true")
        self.assertEqual(module["format"], "halcyon is not a command here")

    def test_waybar_css_uses_gtk3_syntax_only(self) -> None:
        css = render.render_waybar_css(self.tokens)
        self.assertIn("@define-color", css)
        # GTK3 is not a browser: these silently do nothing.
        self.assertNotIn("backdrop-filter", css)
        self.assertNotIn("var(--", css)
        self.assertNotIn(":root", css)

    def test_waybar_css_colours_are_all_defined_before_use(self) -> None:
        css = render.render_waybar_css(self.tokens)
        defined = set(re.findall(r"@define-color\s+([\w-]+)", css))
        used = set(re.findall(r"@([\w-]+)", css)) - {"define-color", "keyframes"}
        self.assertTrue(defined)
        self.assertFalse(used - defined, msg=sorted(used - defined))

    def test_hypr_colours_are_in_hyprlands_format(self) -> None:
        text = render.render_hypr_theme_lua(self.tokens, self.settings)
        for value in re.findall(r"rgba\(([^)]*)\)", text):
            self.assertRegex(value, r"^[0-9a-f]{8}$", msg=value)

    def test_hyprlock_and_hypridle_render(self) -> None:
        self.assertIn("$", render.render_hyprlock_colors(self.tokens))
        self.assertIn("timeout", render.render_hypridle_timeouts(self.settings))

    def test_write_all_writes_every_artefact(self) -> None:
        written = render.write_all(
            self.tokens,
            self.settings,
            self.catalog,
            self.waybar_base,
            {"HALCYON_TEST": "1"},
        )
        self.assertTrue(written)
        for path in written:
            self.assertTrue(os.path.isfile(path), msg=path)
            self.assertGreater(os.path.getsize(path), 0, msg=path)

    def test_write_atomic_leaves_no_partial_file(self) -> None:
        target = os.path.join(self.root, "out", "thing.txt")
        render.write_atomic(target, "hello")
        with open(target, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "hello")
        leftovers = [
            name
            for name in os.listdir(os.path.dirname(target))
            if name.startswith(".halcyon-")
        ]
        self.assertEqual(leftovers, [])


class TestGeneratedLuaParses(IsolatedHalcyon):
    """If `luac` or `lua` is around, parse what we generate for real."""

    def setUp(self) -> None:
        super().setUp()
        import shutil

        self.lua = next(
            (
                binary
                for binary in ("luac5.4", "luac5.3", "luac", "luajit", "lua")
                if shutil.which(binary)
            ),
            None,
        )
        if self.lua is None:
            self.skipTest("no Lua interpreter available")

    def test_all_generated_lua_parses(self) -> None:
        import subprocess

        settings, tokens = pipeline.build(settings_module.defaults())
        written = render.write_all(
            tokens,
            settings,
            pipeline.load_catalog(),
            pipeline.load_waybar_modules(),
            {},
        )
        check = ["-p"] if "luac" in self.lua else ["-bl" if "jit" in self.lua else "-p"]
        for path in written:
            if not path.endswith(".lua"):
                continue
            done = subprocess.run(
                [self.lua, *check, path], capture_output=True, text=True
            )
            self.assertEqual(done.returncode, 0, msg=f"{path}: {done.stderr}")


if __name__ == "__main__":
    unittest.main()
