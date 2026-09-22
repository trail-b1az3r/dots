"""Settings migration: nobody's configuration gets destroyed."""

from __future__ import annotations

import json
import os
import unittest

from halcyon import SETTINGS_SCHEMA_VERSION, migrate, settings as settings_module

from .helpers import IsolatedHalcyon


class TestPureMigration(unittest.TestCase):
    """`migrate()` touches no files, so these need no fixture."""

    def test_a_current_document_is_unchanged(self) -> None:
        document = {"version": SETTINGS_SCHEMA_VERSION, "appearance": {"mode": "light"}}
        result, notes = migrate.migrate(document)
        self.assertEqual(result, document)
        self.assertEqual(notes, [])

    def test_migrating_twice_changes_nothing_the_second_time(self) -> None:
        first, _ = migrate.migrate({"version": 1, "bar": {"right": ["pulseaudio"]}})
        second, notes = migrate.migrate(first)
        self.assertEqual(first, second)
        self.assertEqual(notes, [])

    def test_the_input_is_not_mutated(self) -> None:
        document = {"version": 1, "bar": {"right": ["pulseaudio"]}}
        snapshot = json.dumps(document, sort_keys=True)
        migrate.migrate(document)
        self.assertEqual(json.dumps(document, sort_keys=True), snapshot)

    def test_unknown_keys_survive(self) -> None:
        # A key this build does not recognise may belong to a newer one.
        # Deleting it loses a setting the user will have to find again.
        document = {
            "version": 1,
            "somethingNew": {"keep": "me"},
            "appearance": {"accentColor": "#ff0000"},
        }
        result, _ = migrate.migrate(document)
        self.assertEqual(result["somethingNew"], {"keep": "me"})
        self.assertEqual(result["appearance"]["accentColor"], "#ff0000")

    def test_the_version_is_bumped(self) -> None:
        result, _ = migrate.migrate({"version": 1})
        self.assertEqual(result["version"], SETTINGS_SCHEMA_VERSION)

    def test_a_missing_version_is_treated_as_the_oldest(self) -> None:
        result, _ = migrate.migrate({"bar": {"right": ["pulseaudio"]}})
        self.assertEqual(result["version"], SETTINGS_SCHEMA_VERSION)
        self.assertEqual(result["bar"]["right"], ["audio"])

    def test_a_nonsense_version_does_not_raise(self) -> None:
        result, _ = migrate.migrate({"version": "banana"})
        self.assertEqual(result["version"], SETTINGS_SCHEMA_VERSION)


class TestBarLayoutMigration(unittest.TestCase):
    def migrate_right(self, names: list) -> list:
        result, _ = migrate.migrate({"version": 1, "bar": {"right": names}})
        return result["bar"]["right"]

    def test_waybar_names_become_ultra_bar_names(self) -> None:
        self.assertEqual(
            self.migrate_right(
                ["custom/menu", "pulseaudio", "custom/control", "battery"]
            ),
            ["launcher", "audio", "systemMenu", "battery"],
        )

    def test_the_second_pulseaudio_instance_becomes_the_microphone(self) -> None:
        self.assertEqual(
            self.migrate_right(["pulseaudio", "pulseaudio#microphone"]),
            ["audio", "microphone"],
        )

    def test_modules_with_no_equivalent_are_dropped_with_a_note(self) -> None:
        result, notes = migrate.migrate(
            {"version": 1, "bar": {"right": ["privacy", "battery"]}}
        )
        self.assertEqual(result["bar"]["right"], ["battery"])
        self.assertTrue(any("privacy" in note for note in notes))

    def test_two_names_mapping_to_one_module_do_not_duplicate_it(self) -> None:
        self.assertEqual(
            self.migrate_right(["pulseaudio", "wireplumber"]), ["audio"]
        )

    def test_names_already_in_the_new_form_are_left_alone(self) -> None:
        self.assertEqual(
            self.migrate_right(["launcher", "clock", "battery"]),
            ["launcher", "clock", "battery"],
        )

    def test_an_unrecognised_name_is_kept_rather_than_dropped(self) -> None:
        self.assertEqual(
            self.migrate_right(["somethingCustom"]), ["somethingCustom"]
        )

    def test_a_non_string_entry_does_not_crash_the_migration(self) -> None:
        self.assertEqual(self.migrate_right([None, 7, "battery"]),
                         [None, 7, "battery"])

    def test_every_migrated_name_is_a_real_module(self) -> None:
        # A migration that produces an id the bar cannot load has moved
        # the breakage rather than fixed it.
        from tests.test_bar import registry_entries

        known = set(registry_entries())
        for target in migrate._WAYBAR_TO_ULTRA.values():
            if target is not None:
                self.assertIn(target, known, msg=target)


class TestRunOnDisk(IsolatedHalcyon):
    def write(self, document: dict) -> None:
        from halcyon import paths

        paths.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(paths.SETTINGS_FILE, "w", encoding="utf-8") as handle:
            json.dump(document, handle)

    def read(self) -> dict:
        from halcyon import paths

        with open(paths.SETTINGS_FILE, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def test_no_settings_file_is_not_a_migration(self) -> None:
        result = migrate.run()
        self.assertFalse(result.migrated)
        self.assertEqual(result.notes, [])

    def test_an_old_file_is_migrated_and_backed_up_first(self) -> None:
        self.write({"version": 1, "bar": {"right": ["pulseaudio"]}})
        result = migrate.run()

        self.assertTrue(result.migrated)
        self.assertEqual(result.from_version, 1)
        self.assertEqual(result.to_version, SETTINGS_SCHEMA_VERSION)

        self.assertIsNotNone(result.backup)
        assert result.backup
        self.assertTrue(os.path.isfile(result.backup))
        with open(result.backup, "r", encoding="utf-8") as handle:
            saved = json.load(handle)
        # The backup is the file as it was, not as it became.
        self.assertEqual(saved["bar"]["right"], ["pulseaudio"])

        self.assertEqual(self.read()["bar"]["right"], ["audio"])

    def test_a_dry_run_writes_nothing(self) -> None:
        self.write({"version": 1, "bar": {"right": ["pulseaudio"]}})
        result = migrate.run(dry_run=True)
        self.assertFalse(result.migrated)
        self.assertIsNone(result.backup)
        self.assertEqual(self.read()["bar"]["right"], ["pulseaudio"])

    def test_running_twice_is_safe(self) -> None:
        self.write({"version": 1, "bar": {"right": ["pulseaudio"]}})
        migrate.run()
        after_first = self.read()
        second = migrate.run()
        self.assertFalse(second.migrated)
        self.assertEqual(self.read(), after_first)

    def test_a_migrated_file_loads(self) -> None:
        self.write({
            "version": 1,
            "bar": {"left": ["custom/menu"], "right": ["pulseaudio"]},
            "appearance": {"accentColor": "#ff8800"},
        })
        migrate.run()
        loaded = settings_module.load()
        self.assertEqual(loaded["appearance"]["accentColor"], "#ff8800")
        self.assertEqual(loaded["bar"]["left"], ["launcher"])

    def test_a_corrupt_file_is_not_silently_replaced(self) -> None:
        from halcyon import paths

        paths.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(paths.SETTINGS_FILE, "w", encoding="utf-8") as handle:
            handle.write("{not json")
        result = migrate.run()
        # Unreadable is not the same as old; migrating would mean writing
        # a file whose contents we never understood.
        self.assertFalse(result.migrated)
        with open(paths.SETTINGS_FILE, "r", encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "{not json")


if __name__ == "__main__":
    unittest.main()
