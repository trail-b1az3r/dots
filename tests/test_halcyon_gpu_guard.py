"""The GPU guard: when the glass effects go off and come back."""

from __future__ import annotations

import importlib.machinery
import json
import shutil
import subprocess
import sys
import importlib.util
import os
import pathlib
import stat
import tempfile
import unittest
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent.parent / "dots/.config/hypr/hyprland/halcyon"
_loader = importlib.machinery.SourceFileLoader("gpu_guard", str(HERE / "gpu-guard"))
_spec = importlib.util.spec_from_loader("gpu_guard", _loader)
guard = importlib.util.module_from_spec(_spec)
_loader.exec_module(guard)


def _run(state, samples):
    """Feed (util, free) samples through decide(), returning the actions taken."""
    actions = []
    for util, free in samples:
        state, action = guard.decide(state, util, free)
        if action:
            actions.append(action)
    return state, actions


class TestDeciding(unittest.TestCase):
    def test_a_busy_gpu_turns_the_effects_off_after_two_samples(self) -> None:
        _state, actions = _run({}, [(90, 6000), (90, 6000)])
        self.assertEqual(actions, ["off"])

    def test_one_busy_sample_does_nothing(self) -> None:
        _state, actions = _run({}, [(95, 6000), (30, 6000)])
        self.assertEqual(actions, [])

    def test_low_video_memory_counts_as_busy_too(self) -> None:
        _state, actions = _run({}, [(10, 1000), (10, 1000)])
        self.assertEqual(actions, ["off"])

    def test_the_threshold_is_exactly_81_percent(self) -> None:
        _state, actions = _run({}, [(81, 6000), (81, 6000)])
        self.assertEqual(actions, [], "81 is not above 81")
        _state, actions = _run({}, [(81.5, 6000), (81.5, 6000)])
        self.assertEqual(actions, ["off"])

    def test_the_effects_come_back_only_after_a_long_calm(self) -> None:
        state = {"suppressed": True}
        _state, actions = _run(state, [(20, 8000)] * (guard.CALM_SAMPLES - 1))
        self.assertEqual(actions, [])
        _state, actions = _run(state, [(20, 8000)] * guard.CALM_SAMPLES)
        self.assertEqual(actions, ["restore"])

    def test_a_middling_gpu_neither_turns_off_nor_restores(self) -> None:
        # Between the two thresholds, the effects stay as they are.
        state = {"suppressed": True}
        _state, actions = _run(state, [(75, 4000)] * 40)
        self.assertEqual(actions, [])

    def test_the_effects_do_not_flicker_at_the_threshold(self) -> None:
        state, actions = _run({}, [(90, 6000), (90, 6000)])
        self.assertEqual(actions, ["off"])
        _state, actions = _run(state, [(80, 6000), (82, 6000)] * 10)
        self.assertEqual(actions, [], "bouncing around 81 must not restore")


class TestGamesAndRebounds(unittest.TestCase):
    """The effects load the GPU themselves: without a game they are left alone, and if taking them away only brings
    the GPU straight back, each wait before they return is longer, so they stop flipping every half minute."""

    HOT = [(95, 6000)] * guard.HOT_SAMPLES

    def test_without_a_game_a_busy_gpu_changes_nothing(self) -> None:
        state = {}
        for util, free in [(99, 500)] * 50:
            state, action = guard.decide(state, util, free, game=False)
            self.assertIsNone(action)

    def flip(self, state, now):
        """Hot until held off at `now`, then calm until restored. Returns the state and when it was restored."""
        for util, free in self.HOT:
            state, action = guard.decide(state, util, free, True, now)
        self.assertEqual(action, "off")
        calm = 0
        while True:
            calm += 1
            state, action = guard.decide(state, 20, 8000, False, now + calm * guard.INTERVAL)
            if action == "restore":
                return state, now + calm * guard.INTERVAL, calm

    def test_busy_again_soon_after_coming_back_doubles_the_wait(self) -> None:
        state, restored, first = self.flip({}, 1000.0)
        self.assertEqual(first, guard.CALM_SAMPLES)
        state, restored, second = self.flip(state, restored + 10)
        self.assertEqual(second, guard.CALM_SAMPLES * 2)
        state, restored, third = self.flip(state, restored + 10)
        self.assertEqual(third, guard.CALM_SAMPLES * 4)

    def test_the_wait_has_a_ceiling(self) -> None:
        state, restored, _ = self.flip({}, 0.0)
        waits = []
        for _ in range(8):
            state, restored, wait = self.flip(state, restored + 5)
            waits.append(wait)
        self.assertEqual(max(waits), guard.CALM_MAX_SAMPLES)

    def test_a_long_quiet_spell_resets_the_wait(self) -> None:
        state, restored, _ = self.flip({}, 0.0)
        state, restored, _ = self.flip(state, restored + 5)
        state, restored, later = self.flip(state, restored + guard.REBOUND_SECONDS + 1)
        self.assertEqual(later, guard.CALM_SAMPLES)

    def test_what_counts_as_a_game(self) -> None:
        self.assertTrue(guard.is_game({"class": "steam_app_1091500", "fullscreen": 0}))
        self.assertTrue(guard.is_game({"class": "gamescope"}))
        self.assertTrue(guard.is_game({"class": "Minecraft* 1.21.4"}))
        self.assertTrue(guard.is_game({"class": "eldenring.exe"}))
        self.assertTrue(guard.is_game({"class": "mpv", "fullscreen": 2}))
        self.assertFalse(guard.is_game({"class": "firefox", "fullscreen": 0}))
        self.assertFalse(guard.is_game({"class": "kitty"}))


class TestHolding(unittest.TestCase):
    """The guard holds the effects off through `effects hold`, which leaves your level and says nothing."""

    def tool(self, home, *args):
        env = {**os.environ, "HOME": home, "XDG_CONFIG_HOME": home + "/c", "XDG_STATE_HOME": home + "/s",
               "PATH": home + "/bin:" + os.environ["PATH"]}
        env.pop("HYPRLAND_INSTANCE_SIGNATURE", None)
        return subprocess.run([sys.executable, str(HERE / "halcyon-theme"), *args], env=env,
                              capture_output=True, text=True, timeout=60)

    def setUp(self) -> None:
        self.home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.home)
        os.makedirs(self.home + "/bin")
        self.sent = pathlib.Path(self.home, "notifications")
        with open(self.home + "/bin/notify-send", "w", encoding="utf-8") as f:
            f.write(f'#!/bin/sh\necho "$@" >> {self.sent}\n')
        os.chmod(self.home + "/bin/notify-send", 0o755)
        cfg = pathlib.Path(self.home, "c/illogical-impulse/config.json")
        cfg.parent.mkdir(parents=True)
        cfg.write_text(json.dumps({"halcyon": {"effects": "full", "theme": "red-sun"}}))
        self.cfg = cfg
        state = pathlib.Path(self.home, "s/halcyon")
        state.mkdir(parents=True)
        (state / "active").write_text("red-sun\n")

    def notifications(self) -> str:
        return self.sent.read_text() if self.sent.exists() else ""

    def test_hold_turns_them_off_quietly_and_keeps_your_level(self) -> None:
        self.assertEqual(self.tool(self.home, "effects").stdout.splitlines()[0], "full")
        result = self.tool(self.home, "effects", "hold", "on")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.tool(self.home, "effects").stdout.splitlines()[0], "off")
        self.assertIn("held off by gpu-guard", self.tool(self.home, "effects").stdout)
        self.assertEqual(json.loads(self.cfg.read_text())["halcyon"]["effects"], "full")
        self.tool(self.home, "effects", "hold", "off")
        self.assertEqual(self.tool(self.home, "effects").stdout.splitlines()[0], "full")
        self.assertEqual(self.notifications(), "")

    def test_choosing_a_level_announces_it_once_and_only_when_it_changes(self) -> None:
        self.tool(self.home, "effects", "light")
        self.assertEqual(self.notifications().count("Effects"), 1)
        self.tool(self.home, "effects", "light")
        self.assertEqual(self.notifications().count("Effects"), 1, "the same level again says nothing")
        self.tool(self.home, "effects", "full", "--quiet")
        self.assertEqual(self.notifications().count("Effects"), 1)


class TestParsing(unittest.TestCase):
    def test_nvidia_csv_gives_utilisation_and_free_memory(self) -> None:
        self.assertEqual(guard.parse_nvidia("87, 6500, 8192\n"), (87.0, 1692.0))

    def test_bad_nvidia_output_is_ignored(self) -> None:
        self.assertIsNone(guard.parse_nvidia("No devices were found\n"))
        self.assertIsNone(guard.parse_nvidia(""))

    def test_a_fake_nvidia_smi_is_used_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as bindir:
            script = os.path.join(bindir, "nvidia-smi")
            with open(script, "w", encoding="utf-8") as handle:
                handle.write("#!/bin/sh\necho '83, 7000, 8192'\n")
            os.chmod(script, os.stat(script).st_mode | stat.S_IEXEC)
            with mock.patch.dict(os.environ, {"PATH": bindir}):
                self.assertEqual(guard.sample_nvidia(), (83.0, 1192.0))

    def test_no_gpu_tools_means_no_sample(self) -> None:
        with tempfile.TemporaryDirectory() as empty, mock.patch.dict(os.environ, {"PATH": empty}):
            self.assertIsNone(guard.sample_nvidia())


if __name__ == "__main__":
    unittest.main()
