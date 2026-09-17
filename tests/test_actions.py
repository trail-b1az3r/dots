"""The action allowlist: the boundary between the LLM and the system."""

from __future__ import annotations

import unittest

from halcyon import actions


class _Stub:
    """A destructive action that records instead of acting.

    The registry's real destructive actions suspend and reboot the
    machine. Confirmation gating is exactly the thing worth testing, and
    exactly the thing that ruins the test run if it is broken — so the
    gate is tested against a stub, never against `session.reboot`.
    """

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def __enter__(self) -> "_Stub":
        self.action = actions.register(
            actions.Action(
                id="test.stub",
                title="Stub",
                category="test",
                description="Records that it ran.",
                handler=self._run,
                params=[actions.Param("value", type="int", minimum=0, maximum=9)],
                destructive=True,
            )
        )
        return self

    def __exit__(self, *_exc: object) -> None:
        actions.REGISTRY.pop("test.stub", None)

    def _run(self, params: dict, _settings: dict) -> tuple[bool, str]:
        self.calls.append(params)
        return True, "ran"


class TestRegistry(unittest.TestCase):
    def test_every_action_is_well_formed(self) -> None:
        self.assertTrue(actions.REGISTRY)
        for action_id, action in actions.REGISTRY.items():
            self.assertEqual(action_id, action.id, msg=action_id)
            self.assertTrue(action.title, msg=action_id)
            self.assertTrue(action.description, msg=action_id)
            self.assertTrue(callable(action.handler), msg=action_id)
            names = [p.name for p in action.params]
            self.assertEqual(len(names), len(set(names)), msg=action_id)
            for param in action.params:
                if param.type == "enum":
                    self.assertTrue(param.choices, msg=f"{action_id}.{param.name}")

    def test_catalog_is_json_safe(self) -> None:
        import json

        json.dumps(actions.catalog())

    def test_unknown_action_is_refused_not_raised(self) -> None:
        result = actions.invoke("rm.minus.rf", {}, settings={})
        self.assertFalse(result.ok)
        self.assertIn("no action", result.message.lower())


class TestValidation(unittest.TestCase):
    def test_undeclared_parameters_are_rejected(self) -> None:
        action = actions.REGISTRY["app.open"]
        with self.assertRaises(actions.ActionError):
            actions.validate(action, {"name": "Files", "command": "rm -rf ~"})

    def test_missing_required_parameter_is_rejected(self) -> None:
        action = actions.REGISTRY["app.open"]
        with self.assertRaises(actions.ActionError):
            actions.validate(action, {})

    def test_enum_is_closed(self) -> None:
        param = actions.Param("mode", type="enum", choices=["light", "dark"])
        self.assertEqual(actions._coerce(param, "DARK"), "dark")
        with self.assertRaises(actions.ActionError):
            actions._coerce(param, "chartreuse")

    def test_numbers_respect_their_range(self) -> None:
        param = actions.Param("level", type="int", minimum=0, maximum=100)
        self.assertEqual(actions._coerce(param, "42"), 42)
        self.assertEqual(actions._coerce(param, 42.7), 42)
        for bad in (-1, 101, "loud"):
            with self.assertRaises(actions.ActionError):
                actions._coerce(param, bad)

    def test_booleans_accept_words_not_nonsense(self) -> None:
        param = actions.Param("on", type="bool")
        self.assertIs(actions._coerce(param, "yes"), True)
        self.assertIs(actions._coerce(param, "off"), False)
        with self.assertRaises(actions.ActionError):
            actions._coerce(param, "maybe")

    def test_paths_stay_inside_the_users_own_files(self) -> None:
        param = actions.Param("target", type="path")
        self.assertTrue(actions._coerce(param, "~/Documents").startswith("/"))
        for escape in ("/etc/shadow", "/proc/self/environ", "~/../../etc/passwd"):
            with self.assertRaises(actions.ActionError):
                actions._coerce(param, escape)

    def test_names_reject_shell_metacharacters(self) -> None:
        param = actions.Param("name", type="name")
        self.assertEqual(actions._coerce(param, "Text Editor"), "Text Editor")
        for injection in ("firefox; rm -rf ~", "$(reboot)", "a`id`b", "x|y"):
            with self.assertRaises(actions.ActionError):
                actions._coerce(param, injection)

    def test_strings_are_bounded(self) -> None:
        param = actions.Param("query", type="string")
        with self.assertRaises(actions.ActionError):
            actions._coerce(param, "x" * 5000)


class TestGating(unittest.TestCase):
    def test_destructive_actions_ask_first(self) -> None:
        with _Stub() as stub:
            result = actions.invoke("test.stub", {"value": 1}, settings={})
            self.assertFalse(result.ok)
            self.assertTrue(result.needs_confirmation)
            self.assertEqual(stub.calls, [])

    def test_confirming_lets_it_through(self) -> None:
        with _Stub() as stub:
            result = actions.invoke(
                "test.stub", {"value": 1}, confirmed=True, settings={}
            )
            self.assertTrue(result.ok)
            self.assertEqual(stub.calls, [{"value": 1}])

    def test_confirmation_can_be_turned_off(self) -> None:
        settings = {"assistant": {"privacy": {"confirmDestructiveActions": False}}}
        with _Stub() as stub:
            result = actions.invoke("test.stub", {"value": 1}, settings=settings)
            self.assertTrue(result.ok)
            self.assertEqual(stub.calls, [{"value": 1}])

    def test_bad_parameters_are_caught_before_confirmation(self) -> None:
        with _Stub() as stub:
            result = actions.invoke("test.stub", {"value": 99}, settings={})
            self.assertFalse(result.ok)
            self.assertFalse(result.needs_confirmation)
            self.assertEqual(stub.calls, [])

    def test_a_failing_handler_does_not_escape(self) -> None:
        def explode(_params: dict, _settings: dict) -> tuple[bool, str]:
            raise RuntimeError("boom")

        actions.register(
            actions.Action(
                id="test.explode",
                title="Explode",
                category="test",
                description="Raises.",
                handler=explode,
            )
        )
        try:
            result = actions.invoke("test.explode", {}, settings={})
            self.assertFalse(result.ok)
            self.assertIn("boom", result.message)
        finally:
            actions.REGISTRY.pop("test.explode", None)

    def test_a_gated_action_is_refused_when_its_setting_is_off(self) -> None:
        gated = [a for a in actions.REGISTRY.values() if a.requires_setting]
        self.assertTrue(gated, "no action is gated on a setting")
        for action in gated:
            result = actions.invoke(action.id, {"query": "weather"}, settings={})
            self.assertFalse(result.ok, msg=action.id)
            self.assertIn(action.requires_setting or "", result.message)


if __name__ == "__main__":
    unittest.main()
