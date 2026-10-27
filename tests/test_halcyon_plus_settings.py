"""`halcyon plus`: Settings > Halcyon > Plus Tiles, turned into the Lua Hyprland loads."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HALCYON = Path(__file__).resolve().parent.parent / "dots/.config/hypr/hyprland/halcyon"
sys.path.insert(0, str(HALCYON))

import halcyon_plus_settings as ps  # noqa: E402


class ResolveTests(unittest.TestCase):
    def test_nothing_stored_gives_the_plus_lua_defaults(self):
        values, notes = ps.resolve(None)
        self.assertEqual(notes, [])
        self.assertEqual(values, {key: spec[2] for key, spec in ps.SETTINGS.items()})

    def test_defaults_match_plus_lua(self):
        text = (HALCYON / "plus.lua").read_text(encoding="utf-8")
        for key, (path, _kind, default, _low, _high, *_option) in ps.SETTINGS.items():
            name = path.split(".")[-1]
            if path == "plus.feedback.enabled":
                continue  # not written in plus.lua; the compositor's default is true
            match = re.search(rf"\b{name} = (\w+),", text)
            self.assertIsNotNone(match, f"{name} is not set in plus.lua")
            self.assertEqual(match.group(1), ps.lua_value(default), name)

    def test_wrong_types_fall_back(self):
        values, notes = ps.resolve({"allTiled": "yes", "step": "big", "minWidth": True})
        self.assertIs(values["allTiled"], False)
        self.assertEqual(values["step"], 40)
        self.assertEqual(values["minWidth"], 120)
        self.assertEqual(len(notes), 3)

    def test_out_of_range_is_clamped(self):
        values, notes = ps.resolve({"minWidth": 5, "feedbackDuration": 99999, "step": 55.6})
        self.assertEqual(values["minWidth"], 20)
        self.assertEqual(values["feedbackDuration"], 3000)
        self.assertEqual(values["step"], 56)
        self.assertEqual(len(notes), 2)

    def test_steps_are_kept_in_order(self):
        values, notes = ps.resolve({"step": 50, "stepFine": 80, "stepCoarse": 20})
        self.assertEqual((values["stepFine"], values["step"], values["stepCoarse"]), (50, 50, 50))
        self.assertEqual(len(notes), 2)


class RenderTests(unittest.TestCase):
    def test_render_is_guarded_and_nested(self):
        values, _ = ps.resolve({"allTiled": True, "feedback": False, "feedbackDuration": 200})
        text = ps.render(values)
        self.assertIn("if hl.dsp and hl.dsp.plus then", text)
        self.assertIn("all_tiled = true,", text)
        self.assertRegex(text, r"feedback = \{\n\s+enabled = false,\n\s+duration = 200,\n\s+\},")
        self.assertEqual(text.count("{"), text.count("}"))

    def test_later_options_are_each_behind_a_check_for_them(self):
        values, _ = ps.resolve({"dragFullscreenEdge": 20, "stripOverFullscreen": True})
        text = ps.render(values)
        self.assertRegex(text, r'if hl\.get_config and hl\.get_config\("binds:drag_fullscreen_edge"\) ~= nil then\n\s+hl\.config\(\{\n\s+binds = \{\n\s+drag_fullscreen_edge = 20,')
        self.assertRegex(text, r'hl\.get_config\("superposition:over_fullscreen"\) ~= nil then\n\s+hl\.config\(\{\n\s+superposition = \{\n\s+over_fullscreen = true,')
        # not in the block that only needs Plus Tiles
        self.assertNotIn("drag_fullscreen_edge", text.split("\nend\n")[0])
        self.assertEqual(text.count("{"), text.count("}"))

    @unittest.skipUnless(shutil.which("luac") or shutil.which("luac5.4") or shutil.which("luajit"), "no Lua compiler")
    def test_render_parses(self):
        values, _ = ps.resolve({})
        with tempfile.NamedTemporaryFile("w", suffix=".lua", delete=False) as f:
            f.write(ps.render(values))
        try:
            luac = shutil.which("luac") or shutil.which("luac5.4")
            cmd = [luac, "-p", f.name] if luac else [shutil.which("luajit"), "-bl", f.name]
            self.assertEqual(subprocess.run(cmd, capture_output=True, check=False).returncode, 0)
        finally:
            os.unlink(f.name)


class CommandTests(unittest.TestCase):
    def run_tool(self, home, *args):
        env = {k: v for k, v in os.environ.items() if k != "HYPRLAND_INSTANCE_SIGNATURE"}
        env.update(HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"), XDG_STATE_HOME=str(home / ".local/state"))
        # No Hyprland on PATH: these tests are about a machine without hyprland-plus, whatever this one has.
        env["PATH"] = os.pathsep.join(p for p in env.get("PATH", "").split(os.pathsep)
                                      if p and not any(Path(p, name).exists() for name in ("Hyprland", "hyprland")))
        return subprocess.run([sys.executable, str(HALCYON / "halcyon-theme"), "plus", *args],
                              capture_output=True, text=True, env=env, check=False)

    def test_apply_writes_the_settings(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            cfg = home / ".config/illogical-impulse/config.json"
            cfg.parent.mkdir(parents=True)
            cfg.write_text(json.dumps({"halcyon": {"plus": {"allTiled": True, "minHeight": 200}}}))
            result = self.run_tool(home, "apply")
            self.assertEqual(result.returncode, 0, result.stderr)
            text = (home / ".local/state/halcyon/plus.lua").read_text()
            self.assertIn("all_tiled = true,", text)
            self.assertIn("min_height = 200,", text)

            shown = self.run_tool(home)
            self.assertIn("plus:min_height", shown.stdout)
            self.assertIn("plus:feedback:enabled", shown.stdout)

            status = json.loads(self.run_tool(home, "status").stdout)
            self.assertTrue(status["applied"])
            self.assertFalse(status["plus"])

    def test_edit_copies_once_and_keeps_your_copy(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            copy = home / ".config/hypr/custom/app_rules.lua"
            first = self.run_tool(home, "edit", "rules")
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(copy.read_text(), (HALCYON / "app_rules.lua").read_text())
            copy.write_text("return {}\n")
            self.run_tool(home, "edit", "rules")
            self.assertEqual(copy.read_text(), "return {}\n")

    def test_bad_usage(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(self.run_tool(Path(d), "edit", "everything").returncode, 2)


if __name__ == "__main__":
    unittest.main()
