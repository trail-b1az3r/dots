"""Power policy: the rules that decide how expensive the desktop is."""

from __future__ import annotations

import os
import unittest

from halcyon import power, settings as settings_module


def state(
    *, percentage: float, plugged: bool = False, present: bool = True
) -> power.BatteryState:
    return power.BatteryState(
        present=present,
        percentage=percentage,
        plugged=plugged,
        charging=plugged,
        status="Charging" if plugged else "Discharging",
    )


class TestPolicy(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = settings_module.defaults()

    def test_on_ac_nothing_is_reduced(self) -> None:
        policy = power.decide(self.settings, state(percentage=20, plugged=True))
        graphics = self.settings["graphics"]
        self.assertEqual(policy.blur_quality, graphics["blurQuality"])
        self.assertEqual(policy.shadow_quality, graphics["shadowQuality"])
        self.assertFalse(policy.low_power_graphics)

    def test_a_desktop_without_a_battery_is_left_alone(self) -> None:
        policy = power.decide(self.settings, state(percentage=100, present=False))
        self.assertEqual(policy.blur_quality, self.settings["graphics"]["blurQuality"])
        self.assertIn("no battery", policy.reason)

    def test_critical_battery_turns_the_expensive_effects_off(self) -> None:
        policy = power.decide(self.settings, state(percentage=5))
        self.assertEqual(policy.blur_quality, "off")
        self.assertEqual(policy.shadow_quality, "off")
        self.assertTrue(policy.low_power_graphics)
        self.assertEqual(policy.profile, "battery-saver")

    def test_low_battery_steps_effects_down_without_killing_them(self) -> None:
        policy = power.decide(self.settings, state(percentage=20))
        self.assertNotEqual(policy.animation_quality, "off")
        self.assertTrue(policy.low_power_graphics)

    def test_the_policy_never_raises_quality(self) -> None:
        # Someone who chose "low" on a desktop does not want a policy
        # deciding they meant "high".
        order = ["off", "low", "medium", "high", "ultra"]
        settings = settings_module.defaults()
        settings["graphics"] = dict(settings["graphics"])
        settings["graphics"].update(
            blurQuality="low", shadowQuality="low", animationQuality="low"
        )
        for percentage in (5, 20, 50, 95):
            policy = power.decide(settings, state(percentage=percentage))
            for chosen, decided in (
                ("low", policy.blur_quality),
                ("low", policy.shadow_quality),
                ("low", policy.animation_quality),
            ):
                self.assertLessEqual(
                    order.index(decided), order.index(chosen), msg=str(percentage)
                )

    def test_adaptive_can_be_switched_off_entirely(self) -> None:
        settings = settings_module.defaults()
        settings["power"] = dict(settings["power"])
        settings["power"]["adaptive"] = dict(settings["power"]["adaptive"])
        settings["power"]["adaptive"]["enabled"] = False
        policy = power.decide(settings, state(percentage=3))
        self.assertEqual(policy.blur_quality, settings["graphics"]["blurQuality"])
        self.assertIn("disabled", policy.reason)

    def test_the_policy_is_json_safe(self) -> None:
        import json

        json.dumps(power.decide(self.settings, state(percentage=50)).as_dict())


class TestPolling(unittest.TestCase):
    def test_polling_slows_down_on_battery(self) -> None:
        settings = settings_module.defaults()
        on_ac = power.refresh_interval(settings, state(percentage=80, plugged=True))
        on_battery = power.refresh_interval(settings, state(percentage=80))
        self.assertGreater(on_battery, on_ac)

    def test_intervals_never_reach_zero(self) -> None:
        settings = settings_module.defaults()
        settings["power"] = dict(settings["power"])
        settings["power"]["refreshIntervals"] = {"acSeconds": 0, "batterySeconds": 0}
        self.assertGreaterEqual(
            power.refresh_interval(settings, state(percentage=80, plugged=True)), 1
        )
        self.assertGreaterEqual(
            power.refresh_interval(settings, state(percentage=80)), 1
        )


class TestBackends(unittest.TestCase):
    def test_only_one_backend_is_ever_chosen(self) -> None:
        # Driving two of these at once is how a laptop ends up with tlp
        # and power-profiles-daemon fighting over the same knobs.
        self.assertIsInstance(power.detect_backend("auto"), str)
        self.assertEqual(power.detect_backend("not-a-backend"), "none")

    def test_an_unavailable_preference_does_not_silently_pick_another(self) -> None:
        available = power.available_backends()
        missing = next(
            (
                name
                for name in ("tlp", "tuned", "power-profiles-daemon")
                if name not in available
            ),
            None,
        )
        if missing is None:
            self.skipTest("every backend is installed here")
        self.assertEqual(power.detect_backend(missing), "none")

    def test_conflict_detection_reports_pairs_not_singles(self) -> None:
        found = power.conflicts()
        self.assertIsInstance(found, list)
        self.assertNotEqual(len(found), 1, "a single daemon is not a conflict")


class TestBatteryReading(unittest.TestCase):
    def test_reading_a_machine_with_no_battery_is_not_an_error(self) -> None:
        reading = power.battery_state()
        self.assertIsInstance(reading.percentage, float)
        self.assertGreaterEqual(reading.percentage, 0.0)
        self.assertLessEqual(reading.percentage, 100.0)

    def test_unreadable_sysfs_files_return_none(self) -> None:
        self.assertIsNone(power._read(os.path.join(os.sep, "nonexistent", "x")))
        self.assertIsNone(power._read_int(os.path.join(os.sep, "nonexistent", "x")))


if __name__ == "__main__":
    unittest.main()
