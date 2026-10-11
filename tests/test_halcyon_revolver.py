"""The revolver widget's pool: parsing, weighting and the launch allow-list."""

from __future__ import annotations

import pathlib
import random
import tempfile
import unittest
from unittest import mock

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dots", ".config", "hypr", "hyprland", "halcyon"))

import revolver  # noqa: E402

NOW = 1_800_000_000.0
DAY = 86400.0

LIBRARY_FOLDERS = '''
"libraryfolders"
{
    "0"
    {
        "path"      "/home/me/.local/share/Steam"
        "apps"
        {
            "220"   "1"
        }
    }
    "1"
    {
        "path"      "/mnt/games/SteamLibrary"
    }
}
'''


def _manifest(appid: str, name: str, last: int) -> str:
    return f'''
"AppState"
{{
    "appid"     "{appid}"
    "name"      "{name}"
    "LastPlayed"    "{last}"
}}
'''


class TestVdf(unittest.TestCase):
    def test_nested_sections_and_quoted_values_parse(self) -> None:
        data = revolver.parse_vdf(LIBRARY_FOLDERS)
        folders = data["libraryfolders"]
        self.assertEqual(folders["0"]["path"], "/home/me/.local/share/Steam")
        self.assertEqual(folders["1"]["path"], "/mnt/games/SteamLibrary")

    def test_comments_and_escaped_quotes_are_handled(self) -> None:
        data = revolver.parse_vdf('// a comment\n"k" "say \\"hi\\""\n')
        self.assertEqual(data["k"], 'say "hi"')

    def test_damage_costs_only_what_follows_it(self) -> None:
        data = revolver.parse_vdf('"good" "yes"\n"broken" {\n"unterminated" "x"')
        self.assertEqual(data["good"], "yes")


class TestSteamScan(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.root = pathlib.Path(self._dir.name) / "Steam"
        (self.root / "steamapps").mkdir(parents=True)
        other = pathlib.Path(self._dir.name) / "SteamLibrary"
        (other / "steamapps").mkdir(parents=True)
        (self.root / "steamapps" / "libraryfolders.vdf").write_text(
            LIBRARY_FOLDERS.replace("/home/me/.local/share/Steam", str(self.root))
            .replace("/mnt/games/SteamLibrary", str(other)),
            encoding="utf-8",
        )
        (self.root / "steamapps" / "appmanifest_1.acf").write_text(
            _manifest("1245620", "ELDEN RING", int(NOW - 2 * DAY)), encoding="utf-8")
        (self.root / "steamapps" / "appmanifest_2.acf").write_text(
            _manifest("1000", "Steam Linux Runtime 3.0", 0), encoding="utf-8")
        (other / "steamapps" / "appmanifest_3.acf").write_text(
            _manifest("620", "Portal 2", 0), encoding="utf-8")
        (self.root / "steamapps" / "appmanifest_4.acf").write_text(
            _manifest("abc", "Not a number", 0), encoding="utf-8")

    def test_games_come_from_every_library_and_tools_are_left_out(self) -> None:
        games = revolver.steam_games(self.root, NOW)
        names = sorted(g.name for g in games)
        self.assertEqual(names, ["ELDEN RING", "Portal 2"])

    def test_a_non_numeric_id_is_never_listed(self) -> None:
        self.assertNotIn("Not a number", [g.name for g in revolver.steam_games(self.root, NOW)])


class TestWeights(unittest.TestCase):
    def test_uniform_mode_ignores_play_history(self) -> None:
        self.assertEqual(revolver.weight("random", NOW - DAY, NOW), revolver.weight("random", None, NOW))

    def test_recent_mode_favours_last_week_over_last_year(self) -> None:
        week = revolver.weight("recent", NOW - 7 * DAY, NOW)
        year = revolver.weight("recent", NOW - 365 * DAY, NOW)
        self.assertGreater(week, year)

    def test_recommended_mode_is_lowest_in_the_middle_months(self) -> None:
        yesterday = revolver.weight("recommended", NOW - DAY, NOW)
        middle = revolver.weight("recommended", NOW - 120 * DAY, NOW)
        forgotten = revolver.weight("recommended", NOW - 500 * DAY, NOW)
        self.assertLess(middle, yesterday)
        self.assertLess(middle, forgotten)

    def test_every_weight_is_positive(self) -> None:
        for mode in revolver.MODES:
            for days in (0, 1, 30, 120, 400, 2000):
                self.assertGreater(revolver.weight(mode, NOW - days * DAY, NOW), 0)

    def test_drawing_follows_the_weights(self) -> None:
        heavy = revolver.Chamber("1", "Heavy", "steam", 1000.0)
        light = revolver.Chamber("2", "Light", "steam", 1.0)
        rng = random.Random(7)
        picks = [revolver.draw([heavy, light], rng).id for _ in range(500)]
        self.assertGreater(picks.count("1"), 450)

    def test_an_empty_pool_draws_nothing(self) -> None:
        self.assertIsNone(revolver.draw([]))


class TestPrism(unittest.TestCase):
    def test_instances_read_their_name_and_last_launch(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            instance = pathlib.Path(root) / "1.20.1"
            instance.mkdir()
            (instance / "instance.cfg").write_text(
                "name=Vanilla 1.20\nlastLaunchTime=1799913600000\n", encoding="utf-8")
            (pathlib.Path(root) / "not a folder.txt").write_text("", encoding="utf-8")
            chambers = revolver.prism_instances(pathlib.Path(root))
        self.assertEqual(len(chambers), 1)
        self.assertEqual(chambers[0].name, "Vanilla 1.20")
        self.assertEqual(chambers[0].id, "1.20.1")
        self.assertAlmostEqual(chambers[0].last_played, 1799913600.0)


class TestLaunching(unittest.TestCase):
    def test_a_steam_id_becomes_a_fixed_argument_list(self) -> None:
        self.assertEqual(revolver.launch_argv("steam", "1245620"),
                         ["xdg-open", "steam://rungameid/1245620"])

    def test_text_that_is_not_an_id_is_refused_before_anything_runs(self) -> None:
        for bad in ("1;rm -rf ~", "../../bin/sh", "", "12 34"):
            with self.assertRaises(revolver.LaunchError, msg=bad):
                revolver.launch_argv("steam", bad)

    def test_a_prism_instance_name_with_shell_characters_is_refused(self) -> None:
        with self.assertRaises(revolver.LaunchError):
            revolver.launch_argv("prismlauncher", "x; reboot")

    def test_firing_uses_the_runner_and_never_a_shell(self) -> None:
        captured: list[list[str]] = []
        argv = revolver.fire("prismlauncher", "1.20.1", runner=captured.append)
        self.assertEqual(argv, ["prismlauncher", "--launch", "1.20.1"])
        self.assertEqual(captured, [argv])

    def test_an_unknown_source_is_refused(self) -> None:
        with self.assertRaises(revolver.LaunchError):
            revolver.launch_argv("bash", "-c")


class TestPool(unittest.TestCase):
    def test_duplicates_are_removed_and_the_list_is_sorted(self) -> None:
        raw = [
            revolver.Chamber("2", "b", "steam", 1.0),
            revolver.Chamber("1", "A", "steam", 1.0),
            revolver.Chamber("2", "b", "steam", 1.0),
        ]
        with mock.patch.object(revolver, "steam_roots", return_value=[pathlib.Path("/nowhere")]), \
             mock.patch.object(revolver, "steam_games", return_value=raw):
            chambers = revolver.pool("steam", "random", now=NOW)
        self.assertEqual([c.id for c in chambers], ["1", "2"])

    def test_an_unknown_source_or_mode_is_an_error(self) -> None:
        with self.assertRaises(ValueError):
            revolver.pool("epic")
        with self.assertRaises(ValueError):
            revolver.pool("steam", "chaos")



if __name__ == "__main__":
    unittest.main()
