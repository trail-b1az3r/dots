"""The Ultra Bar: layout, module registry, and Waybar's retirement.

The bar is QML, which these tests cannot instantiate. What they can do
is check the contract between the parts that are data — the module
registry, the layout in settings, and what generation writes — which is
where the mistakes that produce an empty bar actually live.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import unittest

from halcyon import pipeline, render, settings as settings_module

from .helpers import IsolatedHalcyon

REPO = pathlib.Path(__file__).resolve().parent.parent
BAR = REPO / "config" / "quickshell" / "halcyon" / "Modules" / "Bar"


def registry_entries() -> dict[str, str]:
    """Module id -> file, read from BarModules.qml."""
    text = (BAR / "BarModules.qml").read_text()
    return dict(
        re.findall(r'id:\s*"([\w.]+)"[^}]*?file:\s*"([^"]+)"', text, re.S)
    )


class TestModuleRegistry(unittest.TestCase):
    def setUp(self) -> None:
        self.entries = registry_entries()

    def test_the_registry_is_not_empty(self) -> None:
        self.assertGreater(len(self.entries), 10)

    def test_every_module_has_a_file_that_exists(self) -> None:
        for module_id, relative in self.entries.items():
            self.assertTrue(
                (BAR / relative).is_file(),
                msg=f"{module_id} -> {relative} does not exist",
            )

    def test_every_module_file_is_reachable_from_the_registry(self) -> None:
        # A module file nobody can name is a module nobody can use.
        declared = {relative for relative in self.entries.values()}
        on_disk = {
            f"modules/{path.name}"
            for path in (BAR / "modules").glob("*.qml")
        }
        self.assertEqual(
            on_disk - declared, set(),
            msg="module files with no registry entry",
        )

    def test_ids_and_files_are_unique(self) -> None:
        self.assertEqual(
            len(self.entries), len(set(self.entries.values())),
            msg="two ids point at the same file",
        )

    def test_every_entry_has_a_name_and_description(self) -> None:
        text = (BAR / "BarModules.qml").read_text()
        blocks = re.findall(r"\{\s*id:.*?\}", text, re.S)
        self.assertEqual(len(blocks), len(self.entries))
        for block in blocks:
            self.assertIn("name:", block)
            self.assertIn("description:", block)


class TestDefaultLayout(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = settings_module.defaults()
        self.bar = self.settings["bar"]
        self.entries = registry_entries()

    def test_every_module_in_the_layout_is_known(self) -> None:
        used = self.bar["left"] + self.bar["center"] + self.bar["right"]
        unknown = [name for name in used if name not in self.entries]
        self.assertEqual(unknown, [], msg="layout names unknown modules")

    def test_the_layout_names_no_waybar_modules(self) -> None:
        # Waybar's ids ("custom/menu", "pulseaudio#microphone") mean
        # nothing to a bar we wrote.
        used = self.bar["left"] + self.bar["center"] + self.bar["right"]
        for name in used:
            self.assertNotIn("/", name, msg=name)
            self.assertNotIn("#", name, msg=name)

    def test_all_three_sections_exist_and_are_lists(self) -> None:
        for side in ("left", "center", "right"):
            self.assertIsInstance(self.bar[side], list, msg=side)

    def test_the_defaults_include_the_essentials(self) -> None:
        used = set(self.bar["left"] + self.bar["center"] + self.bar["right"])
        for essential in ("launcher", "workspaces", "clock"):
            self.assertIn(essential, used)


class TestWaybarIsOptional(IsolatedHalcyon):
    def build(self, fallback: str):
        settings, tokens = pipeline.build(settings_module.defaults())
        settings["bar"]["fallbackBar"] = fallback
        written = render.write_all(
            tokens,
            settings,
            pipeline.load_catalog(),
            pipeline.load_waybar_modules(),
            {},
        )
        return [os.path.basename(path) for path in written]

    def test_nothing_for_waybar_is_written_by_default(self) -> None:
        names = self.build("none")
        self.assertNotIn("waybar-config.jsonc", names)
        self.assertNotIn("waybar-colors.css", names)

    def test_waybar_files_appear_when_it_is_asked_for(self) -> None:
        names = self.build("waybar")
        self.assertIn("waybar-config.jsonc", names)
        self.assertIn("waybar-colors.css", names)

    def test_turning_it_off_removes_the_files_it_left(self) -> None:
        # A stale config would keep halcyon-bar.service's
        # ConditionPathExists satisfied and start a bar nobody asked for.
        self.build("waybar")
        from halcyon import paths

        config = paths.GENERATED_DIR / "waybar-config.jsonc"
        self.assertTrue(config.is_file())

        self.build("none")
        self.assertFalse(config.is_file())

    def test_the_default_is_none(self) -> None:
        self.assertEqual(
            settings_module.defaults()["bar"]["fallbackBar"], "none"
        )


class TestWaybarIsNotRequired(unittest.TestCase):
    def test_waybar_is_not_a_core_dependency(self) -> None:
        text = (REPO / "deps" / "roles.conf").read_text()
        for line in text.splitlines():
            if line.strip().startswith("waybar"):
                tier = line.split("|")[1].strip()
                self.assertNotEqual(
                    tier, "core",
                    msg="Halcyon's own bar needs no package",
                )
                return
        self.fail("no waybar role found")

    def test_hyprland_does_not_autostart_waybar(self) -> None:
        text = (REPO / "config" / "hypr" / "halcyon" / "autostart.lua").read_text()
        live = [
            line for line in text.splitlines()
            if "waybar" in line.lower() and not line.strip().startswith("--")
        ]
        self.assertEqual(live, [], msg="autostart still launches waybar")

    def test_the_waybar_unit_is_guarded(self) -> None:
        text = (REPO / "services" / "halcyon-bar.service").read_text()
        # It must not start unless the config it needs was generated,
        # which only happens when someone opted in.
        self.assertIn("ConditionPathExists", text)


class TestSystemStats(unittest.TestCase):
    """The data the bar's system modules read, now that Waybar is gone."""

    def test_a_snapshot_is_json_safe(self) -> None:
        from halcyon import sysstat

        json.dumps(sysstat.snapshot(persist=False).as_dict())

    def test_memory_is_reported(self) -> None:
        from halcyon import sysstat

        memory = sysstat.memory()
        self.assertGreater(memory.total_kb, 0)
        self.assertGreaterEqual(memory.percent, 0.0)
        self.assertLessEqual(memory.percent, 100.0)

    def test_cpu_needs_two_samples_and_says_so(self) -> None:
        import time

        from halcyon import sysstat

        sampler = sysstat.CpuSampler()
        # One sample cannot be a rate; None is the honest answer, and a
        # module that showed 0% here would be showing a number it made up.
        self.assertIsNone(sampler.sample())

        # Two readings taken in the same jiffy are also not a rate. Wait
        # for the counters to actually advance before asking again.
        deadline = time.monotonic() + 2.0
        value = None
        while value is None and time.monotonic() < deadline:
            time.sleep(0.05)
            value = sampler.sample()
        self.assertIsNotNone(value, "no reading after two seconds")
        self.assertGreaterEqual(value, 0.0)
        self.assertLessEqual(value, 100.0)

    def test_identical_samples_are_not_reported_as_zero(self) -> None:
        from halcyon import sysstat

        sampler = sysstat.CpuSampler()
        times = sysstat.CpuTimes(total=1000, idle=900)
        self.assertIsNone(sampler._compare(times))
        # The same counters again: no time has passed, so there is no
        # rate — not 0%, which would read as a genuinely idle machine.
        self.assertIsNone(sampler._compare(times))

    def test_a_machine_with_no_sensor_reports_none_not_zero(self) -> None:
        from halcyon import sysstat

        value = sysstat.cpu_temperature()
        if value is None:
            return
        self.assertGreater(value, 0.0)
        self.assertLess(value, 150.0)

    def test_disk_percentages_are_sane(self) -> None:
        from halcyon import sysstat

        usage = sysstat.disk("/")
        self.assertGreater(usage.total_bytes, 0)
        self.assertGreaterEqual(usage.percent, 0.0)
        self.assertLessEqual(usage.percent, 100.0)

    def test_human_bytes(self) -> None:
        from halcyon import sysstat

        self.assertEqual(sysstat.human_bytes(512), "512 B")
        self.assertEqual(sysstat.human_bytes(2048), "2.0 kB")
        self.assertEqual(sysstat.human_bytes(1536 * 1024), "1.5 MB")

    def test_an_unreadable_proc_does_not_raise(self) -> None:
        from halcyon import sysstat

        original = sysstat.PROC
        try:
            sysstat.PROC = "/nonexistent"
            self.assertIsNone(sysstat._read_cpu_times())
            self.assertEqual(sysstat.memory().total_kb, 0)
        finally:
            sysstat.PROC = original


if __name__ == "__main__":
    unittest.main()
