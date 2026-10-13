"""`halcyon config-check`: the checks themselves, without a running Hyprland."""

from __future__ import annotations

import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dots", ".config", "hypr", "hyprland", "halcyon"))

import halcyon_config_check as cc  # noqa: E402


class ChordTests(unittest.TestCase):
    def test_good_chords(self):
        for chord in ("SUPER + Q", "SUPER + SHIFT + Return", "SUPER + F10 + H", "CTRL + ALT + Delete", "Escape", "catchall", "SUPER + mouse:272"):
            self.assertEqual(cc.check_chord(chord), [], chord)

    def test_bad_chords(self):
        self.assertTrue(cc.check_chord(""))
        self.assertIn("Return", cc.check_chord("SUPER + Enter")[0])
        self.assertTrue(any("modifiers must come first" in p for p in cc.check_chord("Q + SUPER")))
        self.assertTrue(any("only modifiers" in p for p in cc.check_chord("SUPER + SHIFT")))
        self.assertTrue(any("empty part" in p for p in cc.check_chord("SUPER + + Q")))
        self.assertTrue(any("space" in p for p in cc.check_chord("SUPER + Page Up")))


class DuplicateBindTests(unittest.TestCase):
    def bind(self, key, desc, dispatcher="exec", arg="x", submap="", mods=64):
        return {"key": key, "description": desc, "dispatcher": dispatcher, "arg": arg, "submap": submap, "modmask": mods}

    def test_two_described_binds_on_one_chord(self):
        found = cc.find_duplicate_binds([self.bind("Q", "App: one", arg="a"), self.bind("Q", "App: two", arg="b")])
        self.assertEqual(len(found), 1)
        self.assertIn("App: one", found[0].message)

    def test_helpers_and_submaps_do_not_count(self):
        binds = [
            self.bind("Q", "App: one"),
            self.bind("Q", "", dispatcher="global", arg="quickshell:searchToggleReleaseInterrupt"),  # Super-tap companion
            self.bind("Q", "Hypr mode: other", submap="hypr", arg="b"),  # another submap
            self.bind("SUPER_L", "Shell: Toggle search", arg="1"),
            self.bind("SUPER_L", "Shell: Toggle search too", arg="2"),
        ]
        self.assertEqual(cc.find_duplicate_binds(binds), [])

    def test_same_action_twice_is_not_a_conflict(self):
        self.assertEqual(cc.find_duplicate_binds([self.bind("Q", "App: one"), self.bind("Q", "App: one again")]), [])


class RepeatedLineTests(unittest.TestCase):
    def test_repeated_rule(self):
        text = 'hl.bind("SUPER + Q", hl.dsp.window.close())\n-- note\nhl.bind("SUPER + Q", hl.dsp.window.close())\n'
        found = cc.find_repeated_lines({"custom/keys.lua": text})
        self.assertEqual(len(found), 1)
        self.assertIn("line 3 repeats line 1", found[0].message)

    def test_other_lines_are_ignored(self):
        self.assertEqual(cc.find_repeated_lines({"a.lua": "local x = 1\nlocal x = 1\n"}), [])


class PluginTests(unittest.TestCase):
    def test_missing_plugin(self):
        found = cc.find_missing_plugins({"a.lua": 'hl.plugin.load("/nonexistent/libhyprbars.so")'})
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].severity, "error")

    def test_existing_plugin(self):
        with tempfile.NamedTemporaryFile(suffix=".so") as so:
            self.assertEqual(cc.find_missing_plugins({"a.lua": f'hl.plugin.load("{so.name}")'}), [])


class PlusOptionTests(unittest.TestCase):
    DEFAULTS = {"plus:enabled": True, "plus:all_tiled": False, "plus:edit_submap": "plus-edit", "plus:step": 40, "plus:step_fine": 10,
                "plus:step_coarse": 160, "plus:min_width": 120, "plus:min_height": 90, "plus:max_width": 0, "plus:max_height": 0,
                "superposition:size": 0.12, "superposition:reserve": False}

    def test_defaults_are_clean(self):
        self.assertEqual(cc.check_plus_options(self.DEFAULTS, plus_submap_binds=20), [])

    def test_steps_out_of_order(self):
        found = cc.check_plus_options({**self.DEFAULTS, "plus:step_fine": 80, "plus:step_coarse": 20}, 20)
        self.assertEqual(len(found), 2)

    def test_min_above_max(self):
        found = cc.check_plus_options({**self.DEFAULTS, "plus:min_width": 500, "plus:max_width": 300}, 20)
        self.assertEqual([f.severity for f in found], ["error"])

    def test_max_zero_means_no_limit(self):
        self.assertEqual(cc.check_plus_options({**self.DEFAULTS, "plus:min_width": 500, "plus:max_width": 0}, 20), [])

    def test_undefined_edit_submap(self):
        found = cc.check_plus_options(self.DEFAULTS, plus_submap_binds=0)
        self.assertEqual(len(found), 1)
        self.assertIn("plus-edit", found[0].message)

    def test_big_reserved_strip(self):
        found = cc.check_plus_options({**self.DEFAULTS, "superposition:reserve": True, "superposition:size": 0.45}, 20)
        self.assertEqual(len(found), 1)


class ConfigErrorTests(unittest.TestCase):
    def test_plus_option_without_plus(self):
        found = cc.classify_config_errors(['config option "plus:step" does not exist'], has_plus=False)
        self.assertEqual(found[0].area, "version")

    def test_plus_option_with_plus_is_a_plain_error(self):
        found = cc.classify_config_errors(['config option "plus:stepp" does not exist'], has_plus=True)
        self.assertEqual(found[0].area, "config")

    def test_keybind_error(self):
        self.assertEqual(cc.classify_config_errors(["Unknown keysym: \"Enter\""], has_plus=True)[0].area, "keybinds")


class PermissionTests(unittest.TestCase):
    def test_world_writable_and_not_executable(self):
        with tempfile.TemporaryDirectory() as d:
            conf = Path(d) / "hyprland.lua"
            conf.write_text("-- x")
            conf.chmod(0o666)
            script = Path(d) / "halcyon-theme"
            script.write_text("#!/bin/sh\n")
            script.chmod(0o644)

            found = cc.check_permissions([conf, script], os.getuid(), [script])
            kinds = sorted(f.autofix for f in found if f.autofix)
            self.assertEqual(kinds, ["chmod+x", "chmod-go-w"])

            done = cc.apply_fixes(found)
            self.assertEqual(len(done), 2)
            self.assertFalse(conf.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH))
            self.assertTrue(os.access(script, os.X_OK))
            # fixed files are clean on a second check
            self.assertEqual([f for f in cc.check_permissions([conf, script], os.getuid(), [script]) if f.autofix], [])


if __name__ == "__main__":
    unittest.main()
