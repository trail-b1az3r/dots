"""Settings: merging, coercion, and refusing typos."""

from __future__ import annotations

import json
import unittest

from halcyon import settings as settings_module

from .helpers import IsolatedHalcyon


class TestMerge(unittest.TestCase):
    def test_deep_merge_preserves_untouched_keys(self) -> None:
        base = {"a": {"b": 1, "c": 2}, "d": 3}
        overlay = {"a": {"b": 9}}
        merged = settings_module.deep_merge(base, overlay)
        self.assertEqual(merged, {"a": {"b": 9, "c": 2}, "d": 3})

    def test_lists_replace_rather_than_append(self) -> None:
        # A user who reorders their bar modules means that order, not
        # that order unioned with ours.
        base = {"bar": {"left": ["a", "b", "c"]}}
        overlay = {"bar": {"left": ["c"]}}
        merged = settings_module.deep_merge(base, overlay)
        self.assertEqual(merged["bar"]["left"], ["c"])

    def test_merge_does_not_mutate_its_inputs(self) -> None:
        base = {"a": {"b": 1}}
        overlay = {"a": {"b": 2}}
        settings_module.deep_merge(base, overlay)
        self.assertEqual(base["a"]["b"], 1)


class TestStore(IsolatedHalcyon):
    def setUp(self) -> None:
        super().setUp()
        import importlib

        from halcyon import settings

        importlib.reload(settings)
        self.settings = settings

    def test_defaults_load(self) -> None:
        loaded = self.settings.load()
        self.assertIn("glass", loaded)
        self.assertIn("assistant", loaded)
        self.assertEqual(loaded["version"], 1)

    def test_set_coerces_to_the_declared_type(self) -> None:
        self.settings.set_value("glass.opacity", "0.42")
        self.assertIsInstance(self.settings.get("glass.opacity"), float)
        self.assertAlmostEqual(self.settings.get("glass.opacity"), 0.42)

        self.settings.set_value("motion.reducedMotion", "true")
        self.assertIs(self.settings.get("motion.reducedMotion"), True)

        self.settings.set_value("bar.height", "40")
        self.assertIsInstance(self.settings.get("bar.height"), int)

    def test_set_rejects_unknown_paths(self) -> None:
        # A typo should be an error, not a setting that silently never
        # takes effect.
        with self.assertRaises(self.settings.SettingsError):
            self.settings.set_value("glass.opacitee", "0.5")

    def test_set_rejects_bad_values(self) -> None:
        with self.assertRaises(self.settings.SettingsError):
            self.settings.set_value("glass.opacity", "very transparent")

    def test_unset_restores_the_default(self) -> None:
        original = self.settings.get("glass.opacity")
        self.settings.set_value("glass.opacity", 0.1)
        self.settings.unset("glass.opacity")
        self.assertEqual(self.settings.get("glass.opacity"), original)

    def test_unset_prunes_empty_containers(self) -> None:
        self.settings.set_value("glass.opacity", 0.1)
        self.settings.unset("glass.opacity")
        self.assertNotIn("glass", self.settings.user_settings())

    def test_only_overrides_are_written(self) -> None:
        self.settings.set_value("glass.opacity", 0.33)
        with open(self.paths.SETTINGS_FILE, encoding="utf-8") as handle:
            written = json.load(handle)
        self.assertEqual(set(written) - {"version"}, {"glass"})
        self.assertEqual(written["glass"], {"opacity": 0.33})

    def test_a_newer_schema_is_refused(self) -> None:
        self.paths.SETTINGS_FILE.write_text('{"version": 99}', encoding="utf-8")
        with self.assertRaises(self.settings.SettingsError):
            self.settings.load()


if __name__ == "__main__":
    unittest.main()
