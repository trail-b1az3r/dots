"""The GPU guard: when the glass effects go off and come back."""

from __future__ import annotations

import importlib.machinery
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
