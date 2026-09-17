"""The assistant: deterministic intents first, model second."""

from __future__ import annotations

import json
import unittest

from halcyon import actions
from halcyon.assistant import intents, protocol

from .helpers import IsolatedHalcyon


class TestIntentParsing(unittest.TestCase):
    def assert_intent(self, utterance: str, action: str, **params: object) -> None:
        intent = intents.parse(utterance)
        self.assertIsNotNone(intent, msg=utterance)
        assert intent
        self.assertEqual(intent.action, action, msg=utterance)
        for key, value in params.items():
            self.assertEqual(intent.params.get(key), value, msg=f"{utterance}:{key}")

    def test_volume(self) -> None:
        self.assert_intent("set the volume to 30%", "volume.set", percent=30)
        self.assert_intent("turn the volume up", "volume.adjust", delta=10)
        self.assert_intent("turn the volume down by 20", "volume.adjust", delta=-20)

    def test_brightness(self) -> None:
        self.assert_intent("set brightness to 70", "brightness.set", percent=70)
        self.assert_intent("brightness up", "brightness.adjust", delta=10)

    def test_applications(self) -> None:
        self.assert_intent("open firefox", "app.open", name="firefox")
        self.assert_intent("launch the terminal", "app.open")

    def test_workspaces(self) -> None:
        self.assert_intent("switch to workspace 3", "workspace.switch", index=3)
        self.assert_intent("go to the second workspace", "workspace.switch", index=2)

    def test_wake_words_and_politeness_are_stripped(self) -> None:
        for prefix in ("hey halcyon, ", "halcyon ", "please ", "could you ", ""):
            self.assert_intent(f"{prefix}set the volume to 30%", "volume.set", percent=30)

    def test_out_of_range_values_are_clamped_or_refused(self) -> None:
        intent = intents.parse("switch to workspace 99")
        # 99 is outside the workspace range, so this is not a command —
        # better to let the model say so than to switch to workspace 9.
        self.assertIsNone(intent)

    def test_questions_are_left_for_the_model(self) -> None:
        for question in (
            "what is the capital of France",
            "why is the sky blue",
            "write me a haiku about wayland",
            "",
            "   ",
        ):
            self.assertIsNone(intents.parse(question), msg=question)

    def test_every_rule_names_a_registered_action(self) -> None:
        # A rule pointing at an action that does not exist is a silent
        # dead end; parse() drops it, so this is the only place it shows.
        samples = [
            "open firefox", "close firefox", "set the volume to 30%",
            "volume up", "volume down", "set brightness to 50",
            "brightness up", "brightness down", "switch to workspace 2",
            "take a screenshot", "lock the screen", "next track",
            "pause the music", "turn on do not disturb", "what's my battery",
        ]
        for sample in samples:
            intent = intents.parse(sample)
            if intent is not None:
                self.assertIn(intent.action, actions.REGISTRY, msg=sample)

    def test_parsed_intents_survive_action_validation(self) -> None:
        # Parsing something the allowlist then rejects is the worst case:
        # the user is told their own phrasing is wrong.
        samples = [
            "set the volume to 30%", "turn the volume up",
            "set brightness to 70", "switch to workspace 3", "open firefox",
        ]
        for sample in samples:
            intent = intents.parse(sample)
            assert intent, sample
            action = actions.REGISTRY[intent.action]
            actions.validate(action, intent.params)

    def test_confidence_is_a_probability(self) -> None:
        intent = intents.parse("set the volume to 30%")
        assert intent
        self.assertGreater(intent.confidence, 0.0)
        self.assertLessEqual(intent.confidence, 1.0)


class TestProtocol(IsolatedHalcyon):
    def test_the_socket_lives_in_the_runtime_directory(self) -> None:
        import importlib

        importlib.reload(protocol)
        path = protocol.socket_path()
        self.assertTrue(path.startswith(self.root), msg=path)

    def test_events_round_trip_as_ndjson(self) -> None:
        # Newlines frame the protocol, so text containing one must not be
        # able to split a message into two.
        event = protocol.Event(event="token", text="hello\nworld")
        encoded = event.encode()
        self.assertEqual(encoded.count(b"\n"), 1)
        self.assertTrue(encoded.endswith(b"\n"))

        decoded = protocol.Event.decode(encoded)
        self.assertEqual(decoded.event, "token")
        self.assertEqual(decoded.text, "hello\nworld")

    def test_a_malformed_line_raises_rather_than_returning_a_blank(self) -> None:
        with self.assertRaises(json.JSONDecodeError):
            protocol.Event.decode(b"not json\n")

    def test_missing_fields_decode_to_empty_ones(self) -> None:
        decoded = protocol.Event.decode(b'{"event":"done"}')
        self.assertEqual(decoded.event, "done")
        self.assertEqual(decoded.text, "")
        self.assertEqual(decoded.data, {})


if __name__ == "__main__":
    unittest.main()
