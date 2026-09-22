"""The keybind registry — the system that must never silently fail."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest

from halcyon import keybinds, pipeline, render, settings as settings_module


def catalog(*entries: dict) -> dict:
    return {"version": 2, "binds": list(entries)}


def bind(bind_id: str, chord: str, **extra) -> dict:
    entry = {
        "id": bind_id,
        "chord": chord,
        "description": bind_id,
        "action": {"dsp": "hl.dsp.window.close()"},
    }
    entry.update(extra)
    return entry


class TestChords(unittest.TestCase):
    def test_modifier_order_does_not_matter(self) -> None:
        a = keybinds.parse_chord("SUPER + SHIFT + S")
        b = keybinds.parse_chord("SHIFT + SUPER + S")
        self.assertEqual(a.normalised, b.normalised)

    def test_case_does_not_matter(self) -> None:
        a = keybinds.parse_chord("SUPER + T")
        b = keybinds.parse_chord("super + t")
        self.assertEqual(a.normalised, b.normalised)

    def test_whitespace_is_irrelevant(self) -> None:
        self.assertEqual(
            keybinds.parse_chord("SUPER+SHIFT+S").normalised,
            keybinds.parse_chord("  SUPER  +  SHIFT  +  S ").normalised,
        )

    def test_different_chords_stay_different(self) -> None:
        self.assertNotEqual(
            keybinds.parse_chord("SUPER + S").normalised,
            keybinds.parse_chord("SUPER + SHIFT + S").normalised,
        )

    def test_a_bare_key_parses(self) -> None:
        chord = keybinds.parse_chord("XF86AudioPlay")
        self.assertEqual(chord.mods, ())
        self.assertEqual(chord.key, "XF86AudioPlay")

    def test_an_empty_chord_is_rejected(self) -> None:
        for bad in ("", "   ", "+", " + + "):
            with self.assertRaises(keybinds.CatalogError, msg=bad):
                keybinds.parse_chord(bad)


class TestValidation(unittest.TestCase):
    def build(self, *entries: dict, overrides: dict | None = None):
        return keybinds.build(
            catalog(*entries), overrides or {}, check_executables=False
        )

    def test_a_valid_binding_is_accepted(self) -> None:
        registry = self.build(bind("ok", "SUPER + T"))
        self.assertEqual(len(registry.bindings), 1)
        self.assertEqual(registry.errors, [])

    def test_duplicate_chords_are_reported_not_dropped_silently(self) -> None:
        registry = self.build(bind("first", "SUPER + T"), bind("second", "SUPER + T"))
        self.assertEqual([b.id for b in registry.bindings], ["first"])
        self.assertEqual(len(registry.errors), 1)
        problem = registry.errors[0]
        self.assertEqual(problem.binding, "second")
        self.assertIn("first", problem.owner or "")
        self.assertIn("second", problem.resolution)
        self.assertTrue(problem.source)

    def test_an_invalid_modifier_is_an_error(self) -> None:
        registry = self.build(bind("bad", "HYPER + T"))
        self.assertEqual(registry.bindings, [])
        self.assertIn("modifier", registry.errors[0].message)

    def test_an_unknown_keysym_warns_but_still_binds(self) -> None:
        # Our keysym table is one version of xkbcommon's; the user's
        # keymap may resolve a name we have never heard of.
        registry = self.build(bind("odd", "SUPER + NotAKeysym"))
        self.assertEqual(len(registry.bindings), 1)
        self.assertEqual(registry.errors, [])
        self.assertTrue(registry.warnings)

    def test_real_keysyms_do_not_warn(self) -> None:
        for chord in (
            "SUPER + Space", "XF86AudioRaiseVolume", "SUPER + slash",
            "SUPER + grave", "CTRL + SHIFT + S", "SUPER + Return",
            "SUPER + Escape", "SUPER + Left", "SUPER + F1",
        ):
            registry = self.build(bind("k", chord))
            self.assertEqual(registry.warnings, [], msg=chord)

    def test_mouse_buttons_below_272_are_rejected(self) -> None:
        registry = self.build(bind("m", "SUPER + mouse:1"))
        self.assertEqual(registry.bindings, [])
        self.assertIn("272", registry.errors[0].message)

    def test_valid_mouse_and_scroll_keys_are_accepted(self) -> None:
        for chord in ("SUPER + mouse:272", "SUPER + mouse_down", "SUPER + mouse_up"):
            registry = self.build(bind("m", chord))
            self.assertEqual(len(registry.bindings), 1, msg=chord)
            self.assertEqual(registry.warnings, [], msg=chord)

    def test_a_raw_keycode_is_accepted(self) -> None:
        for chord in ("SUPER + code:24", "SUPER + 24"):
            registry = self.build(bind("k", chord))
            self.assertEqual(len(registry.bindings), 1, msg=chord)

    def test_a_missing_action_is_an_error(self) -> None:
        registry = self.build(bind("x", "SUPER + T", action={}))
        self.assertEqual(registry.bindings, [])
        self.assertIn("no action", registry.errors[0].message)

    def test_an_unknown_action_id_is_an_error(self) -> None:
        registry = self.build(
            bind("x", "SUPER + T", action={"action": "not.a.real.action"})
        )
        self.assertEqual(registry.bindings, [])
        self.assertIn("action registry", registry.errors[0].message)

    def test_a_real_action_id_is_accepted(self) -> None:
        registry = self.build(bind("x", "SUPER + T", action={"action": "volume.mute"}))
        self.assertEqual(len(registry.bindings), 1)

    def test_a_dispatcher_must_be_a_dispatcher(self) -> None:
        registry = self.build(bind("x", "SUPER + T", action={"dsp": "os.execute('id')"}))
        self.assertEqual(registry.bindings, [])
        self.assertIn("hl.dsp.", registry.errors[0].message)

    def test_an_empty_exec_is_an_error(self) -> None:
        registry = self.build(bind("x", "SUPER + T", action={"exec": "   "}))
        self.assertEqual(registry.bindings, [])

    def test_a_missing_executable_warns_but_still_binds(self) -> None:
        registry = keybinds.build(
            catalog(bind("x", "SUPER + T",
                         action={"exec": "definitely-not-installed-xyz"})),
            {},
            check_executables=True,
        )
        self.assertEqual(len(registry.bindings), 1)
        self.assertTrue(registry.warnings)

    def test_a_complex_shell_command_is_not_second_guessed(self) -> None:
        # "$(...)" or a pipeline has no single executable to look up.
        for command in ("$TERMINAL -e vi", "a || b", "foo | bar"):
            self.assertEqual(keybinds._executable_of(command), "",
                             msg=command)


class TestOverrides(unittest.TestCase):
    def test_a_string_override_rebinds(self) -> None:
        registry = keybinds.build(
            catalog(bind("x", "SUPER + T")), {"x": "SUPER + Y"},
            check_executables=False,
        )
        self.assertEqual(registry.bindings[0].chord, "SUPER + Y")
        self.assertEqual(registry.bindings[0].source, "settings.json")

    def test_none_unbinds(self) -> None:
        for value in ("none", "None", "unbound", "disabled", "", False):
            registry = keybinds.build(
                catalog(bind("x", "SUPER + T")), {"x": value},
                check_executables=False,
            )
            self.assertEqual(registry.bindings, [], msg=repr(value))

    def test_an_override_can_create_a_collision_and_it_is_reported(self) -> None:
        registry = keybinds.build(
            catalog(bind("a", "SUPER + T"), bind("b", "SUPER + Y")),
            {"b": "SUPER + T"},
            check_executables=False,
        )
        self.assertEqual([x.id for x in registry.bindings], ["a"])
        self.assertEqual(len(registry.errors), 1)
        self.assertEqual(registry.errors[0].source, "settings.json")


class TestMigration(unittest.TestCase):
    def test_a_version_1_catalog_still_loads(self) -> None:
        v1 = {
            "binds": [
                {"id": "spotlight", "category": "shell", "title": "Spotlight",
                 "default": "SUPER + Space",
                 "run": {"exec": "halcyon shell spotlight toggle"}}
            ],
            "mouseBinds": [
                {"id": "drag", "title": "Drag", "default": "SUPER + mouse:272",
                 "run": {"dsp": "hl.dsp.window.drag()"}}
            ],
        }
        bindings = keybinds.load_catalog(v1, source="v1")
        self.assertEqual(len(bindings), 2)
        by_id = {b.id: b for b in bindings}
        self.assertEqual(by_id["spotlight"].chord, "SUPER + Space")
        self.assertEqual(by_id["spotlight"].description, "Spotlight")
        # The shell requirement is inferred from the command.
        self.assertTrue(by_id["spotlight"].requires_shell)
        self.assertTrue(by_id["drag"].mouse)

    def test_a_newer_schema_is_refused_rather_than_guessed_at(self) -> None:
        with self.assertRaises(keybinds.CatalogError):
            keybinds.load_catalog({"version": 99, "binds": []})


class TestEmergency(unittest.TestCase):
    def test_the_emergency_set_covers_every_required_capability(self) -> None:
        registry = keybinds.Registry(bindings=keybinds.emergency_bindings())
        self.assertEqual(keybinds.emergency_gaps(registry), [])

    def test_emergency_bindings_never_need_the_shell(self) -> None:
        # The case they exist for is the shell being dead.
        for binding in keybinds.emergency_bindings():
            self.assertFalse(binding.requires_shell, msg=binding.id)

    def test_emergency_bindings_are_valid(self) -> None:
        accepted, diagnostics = keybinds.validate(
            keybinds.emergency_bindings(), check_executables=False
        )
        self.assertEqual(len(accepted), len(keybinds.emergency_bindings()))
        self.assertEqual([d for d in diagnostics if d.severity == "error"], [])

    def test_the_shipped_catalog_covers_every_recovery_capability(self) -> None:
        registry = keybinds.build(
            pipeline.load_catalog(), {}, check_executables=False
        )
        self.assertEqual(
            keybinds.emergency_gaps(registry), [],
            "a recovery capability has no working binding",
        )


class TestShippedCatalog(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = pipeline.load_catalog()
        self.registry = keybinds.build(
            self.catalog, {}, check_executables=False
        )

    def test_it_is_schema_version_2(self) -> None:
        self.assertEqual(self.catalog.get("version"), keybinds.SCHEMA_VERSION)

    def test_it_has_no_errors(self) -> None:
        self.assertEqual(
            [d.format() for d in self.registry.errors], [],
        )

    def test_every_binding_has_a_description_and_category(self) -> None:
        for binding in self.registry.bindings:
            self.assertTrue(binding.description, msg=binding.id)
            self.assertTrue(binding.category, msg=binding.id)

    def test_ids_are_unique(self) -> None:
        ids = [b["id"] for b in self.catalog["binds"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_shell_bindings_either_degrade_or_say_why_not(self) -> None:
        for binding in self.registry.bindings:
            if not binding.requires_shell:
                continue
            if keybinds.has_fallback(binding):
                continue
            self.assertFalse(
                binding.degrades,
                msg=f"{binding.id} needs the shell, has no fallback, and "
                    "does not record that as intentional",
            )
            self.assertTrue(binding.degrades_reason, msg=binding.id)


class TestGeneratedLua(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = settings_module.defaults()
        self.lua = None
        import shutil

        for candidate in ("luac", "luac5.4", "luac5.3"):
            if shutil.which(candidate):
                self.lua = candidate
                break

    def render(self, cat: dict) -> str:
        return render.render_hypr_keybinds_lua(self.settings, cat)

    def assert_parses(self, text: str) -> None:
        if self.lua is None:
            self.skipTest("no Lua compiler available")
        with tempfile.NamedTemporaryFile("w", suffix=".lua", delete=False) as handle:
            handle.write(text)
            path = handle.name
        try:
            done = subprocess.run(
                [self.lua, "-p", path], capture_output=True, text=True
            )
            self.assertEqual(done.returncode, 0, msg=done.stderr)
        finally:
            os.unlink(path)

    def test_the_shipped_catalog_generates_parsable_lua(self) -> None:
        self.assert_parses(self.render(pipeline.load_catalog()))

    def test_every_accepted_binding_reaches_the_file(self) -> None:
        registry = keybinds.build(
            pipeline.load_catalog(), {}, check_executables=False
        )
        text = self.render(pipeline.load_catalog())
        for binding in registry.bindings:
            self.assertIn(
                f'hl.bind("{binding.chord}"', text, msg=binding.id
            )

    def test_a_rejected_binding_is_explained_in_the_file(self) -> None:
        text = self.render(catalog(
            bind("a", "SUPER + T"), bind("b", "SUPER + T"),
        ))
        self.assertIn("ERROR", text)
        self.assertIn("already bound", text)

    def test_hostile_catalog_text_cannot_escape_a_lua_comment(self) -> None:
        # Diagnostics quote catalog content back into the file. A newline
        # there would end the comment and make the rest live code.
        for payload in (
            "x\nhl.bind('SUPER + Z', hl.dsp.exit())",
            "x\r\nhl.bind('SUPER + Z', hl.dsp.exit())",
            "]]--\nhl.bind('SUPER + Z', hl.dsp.exit())",
        ):
            text = self.render(catalog(
                bind("evil", "SUPER + T", action={"dsp": payload},
                     description=payload),
            ))
            live = [
                line for line in text.splitlines()
                if "SUPER + Z" in line and not line.lstrip().startswith("--")
            ]
            self.assertEqual(live, [], msg=payload)
            self.assert_parses(text)

    def test_workspace_binds_do_not_collide_with_the_catalog(self) -> None:
        text = self.render(pipeline.load_catalog())
        import re

        chords = re.findall(r'hl\.bind\("([^"]+)"', text)
        normalised = [keybinds.parse_chord(c).normalised for c in chords]
        duplicates = {c for c in normalised if normalised.count(c) > 1}
        self.assertEqual(duplicates, set())


if __name__ == "__main__":
    unittest.main()
