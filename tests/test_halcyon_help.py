"""`halcyon help`: it covers every command, and says plainly that hyprland-plus is not one."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import subprocess
import sys
import unittest
from pathlib import Path

HALCYON = Path(__file__).resolve().parent.parent / "dots/.config/hypr/hyprland/halcyon"
sys.path.insert(0, str(HALCYON))

import halcyon_help as help_text  # noqa: E402

_loader = importlib.machinery.SourceFileLoader("halcyon_theme", str(HALCYON / "halcyon-theme"))
_spec = importlib.util.spec_from_loader("halcyon_theme", _loader)
theme = importlib.util.module_from_spec(_spec)
_loader.exec_module(theme)

# Run by other scripts, not typed.
INTERNAL = {"detach"}
# Handled in main() before the table: they hand over to another program.
HANDED_OVER = {"assistant", "config-check", "plus", "crashes", "text", "usb"}


class CoverageTests(unittest.TestCase):
    def test_every_command_is_in_the_help(self):
        known = set(theme.COMMANDS) | HANDED_OVER
        missing = known - INTERNAL - help_text.commands()
        self.assertEqual(missing, set(), f"add these to halcyon_help.py: {sorted(missing)}")

    def test_help_has_no_command_that_does_not_exist(self):
        extra = help_text.commands() - set(theme.COMMANDS) - HANDED_OVER
        self.assertEqual(extra, set())

    def test_handed_over_commands_really_are_handled(self):
        source = (HALCYON / "halcyon-theme").read_text(encoding="utf-8")
        for name in HANDED_OVER:
            self.assertIn(f'argv[0] == "{name}"', source, name)


class RenderTests(unittest.TestCase):
    def test_full_help_names_the_program_and_the_hyprland_plus_note(self):
        text = help_text.render()
        self.assertIn("Usage: halcyon COMMAND", text)
        self.assertIn("hyprland-plus is not a command", text)
        self.assertIn("hyprctl version", text)

    def test_one_command(self):
        text = help_text.render("auto")
        self.assertIn("auto sun", text)
        self.assertNotIn("revolver", text)
        self.assertNotIn("hyprland-plus is not a command", text)

    def test_unknown_command(self):
        with self.assertRaises(KeyError):
            help_text.render("nope")

    def test_every_row_has_a_description(self):
        for group, rows in help_text.GROUPS:
            for usage, what in rows:
                self.assertTrue(usage.strip() and what.strip(), (group, usage))


class CommandLineTests(unittest.TestCase):
    def run_tool(self, *args):
        env = {k: v for k, v in os.environ.items() if k != "HYPRLAND_INSTANCE_SIGNATURE"}
        return subprocess.run([sys.executable, str(HALCYON / "halcyon-theme"), *args], capture_output=True, text=True, env=env, check=False)

    def test_help_and_topics(self):
        self.assertEqual(self.run_tool("help").returncode, 0)
        self.assertEqual(self.run_tool("--help").returncode, 0)
        self.assertIn("cursor size N", self.run_tool("help", "cursor").stdout)
        bad = self.run_tool("help", "nope")
        self.assertEqual(bad.returncode, 2)

    def test_unknown_command_shows_the_help(self):
        result = self.run_tool("frobnicate")
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown command 'frobnicate'", result.stderr)
        self.assertIn("Themes", result.stderr)


if __name__ == "__main__":
    unittest.main()
