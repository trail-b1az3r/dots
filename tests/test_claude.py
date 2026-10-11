"""The Claude API backend: consent, keys, streaming and what never leaves."""

from __future__ import annotations

import io
import json
import os
import pathlib
import stat
import tempfile
import unittest
import urllib.error
from typing import Any
from unittest import mock

from halcyon.assistant import providers
from halcyon.assistant.providers import claude
from halcyon.assistant.protocol import Event

KEY = "sk-ant-test-0123456789"


def _settings(*, allow: bool, provider: str = "claude") -> dict[str, Any]:
    return {
        "assistant": {
            "provider": provider,
            "privacy": {"allowCloudModels": allow},
            "claude": {"model": "claude-sonnet-5-5", "maxTokens": 256},
        }
    }


class _Stream(io.BytesIO):
    """A response body that also behaves as a context manager, as urlopen's does."""


def _sse(*events: dict[str, Any]) -> _Stream:
    lines = []
    for event in events:
        lines.append(f"event: {event['type']}\n".encode())
        lines.append(b"data: " + json.dumps(event).encode() + b"\n\n")
    return _Stream(b"".join(lines))


def _delta(text: str) -> dict[str, Any]:
    return {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": text}}


class _Isolated(unittest.TestCase):
    """Point the key file at a scratch directory for every test."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.key_file = pathlib.Path(self._dir.name) / "secrets" / "anthropic.key"
        patch = mock.patch.object(claude, "KEY_FILE", self.key_file)
        patch.start()
        self.addCleanup(patch.stop)


class TestConsentAndKeys(_Isolated):
    def test_nothing_is_sent_until_cloud_models_are_allowed(self) -> None:
        provider = claude.ClaudeProvider(_settings(allow=False), env={"ANTHROPIC_API_KEY": KEY})
        ok, message = provider.health()
        self.assertFalse(ok)
        self.assertIn("Allow cloud models", message)

    def test_the_key_comes_from_the_environment_first(self) -> None:
        key, source = claude.read_key({"ANTHROPIC_API_KEY": KEY})
        self.assertEqual((key, source), (KEY, "environment"))

    def test_a_stored_key_is_used_when_the_environment_has_none(self) -> None:
        claude.store_key(KEY)
        key, source = claude.read_key({})
        self.assertEqual((key, source), (KEY, "key file"))

    def test_a_key_file_other_users_can_read_is_refused(self) -> None:
        claude.store_key(KEY)
        os.chmod(self.key_file, 0o644)
        key, source = claude.read_key({})
        self.assertIsNone(key)
        self.assertIn("chmod 600", source)

    def test_storing_a_key_makes_it_owner_only(self) -> None:
        claude.store_key(KEY)
        mode = stat.S_IMODE(os.stat(self.key_file).st_mode)
        self.assertEqual(mode, 0o600)

    def test_a_key_with_spaces_is_refused_rather_than_mangled(self) -> None:
        with self.assertRaises(ValueError):
            claude.store_key("sk-ant one two")
        self.assertFalse(self.key_file.exists())

    def test_forgetting_the_key_removes_it(self) -> None:
        claude.store_key(KEY)
        self.assertTrue(claude.forget_key())
        self.assertFalse(claude.forget_key())
        self.assertIsNone(claude.read_key({})[0])


class TestAnswering(_Isolated):
    def _provider(self, **kwargs: Any) -> claude.ClaudeProvider:
        return claude.ClaudeProvider(_settings(allow=True), env={"ANTHROPIC_API_KEY": KEY}, **kwargs)

    def test_a_reply_is_streamed_and_returned_whole(self) -> None:
        stream = _sse(_delta("Hello"), _delta(", there."), {"type": "message_stop"})
        provider = self._provider()
        events: list[Event] = []
        with mock.patch.object(claude.ClaudeProvider, "_open", staticmethod(lambda *a, **k: stream)):
            text = provider.respond("hi", [], emit=events.append, should_stop=lambda: False)
        self.assertEqual(text, "Hello, there.")
        deltas = [e.text for e in events if e.event == "delta"]
        self.assertEqual(deltas, ["Hello", ", there."])

    def test_the_request_carries_the_key_and_the_model_but_no_secrets_in_the_body(self) -> None:
        captured: dict[str, Any] = {}

        def fake_open(request, timeout):
            captured["headers"] = {k.lower(): v for k, v in request.header_items()}
            captured["body"] = json.loads(request.data.decode())
            return _sse({"type": "message_stop"})

        with mock.patch.object(claude.ClaudeProvider, "_open", staticmethod(fake_open)):
            self._provider().respond("what is rust", [], emit=lambda e: None, should_stop=lambda: False)
        self.assertEqual(captured["headers"]["x-api-key"], KEY)
        self.assertEqual(captured["headers"]["anthropic-version"], claude.API_VERSION)
        self.assertEqual(captured["body"]["model"], "claude-sonnet-5-5")
        self.assertEqual(captured["body"]["max_tokens"], 256)
        self.assertTrue(captured["body"]["stream"])
        self.assertNotIn(KEY, json.dumps(captured["body"]))

    def test_commands_are_run_here_and_never_sent(self) -> None:
        def must_not_call(*_a, **_k):
            raise AssertionError("a command must not reach the network")

        provider = self._provider()
        with mock.patch.object(claude.ClaudeProvider, "_open", staticmethod(must_not_call)), \
             mock.patch("halcyon.assistant.providers.local.LocalProvider._run_intent",
                        return_value="done") as run:
            result = provider.respond("turn the volume up", [], emit=lambda e: None, should_stop=lambda: False)
        self.assertEqual(result, "done")
        run.assert_called_once()

    def test_an_error_is_reported_without_the_key(self) -> None:
        def rejected(request, timeout):
            raise urllib.error.HTTPError(
                request.full_url, 401, "Unauthorized", {}, io.BytesIO(b'{"error":{"message":"bad key"}}')
            )

        events: list[Event] = []
        with mock.patch.object(claude.ClaudeProvider, "_open", staticmethod(rejected)):
            text = self._provider().respond("hello there", [], emit=events.append, should_stop=lambda: False)
        self.assertIn("rejected the API key", text)
        self.assertNotIn(KEY, text)
        self.assertTrue(any(e.event == "error" for e in events))

    def test_a_dropped_network_is_a_clear_message(self) -> None:
        def unreachable(request, timeout):
            raise urllib.error.URLError("no route")

        with mock.patch.object(claude.ClaudeProvider, "_open", staticmethod(unreachable)):
            text = self._provider().respond("hello there", [], emit=lambda e: None, should_stop=lambda: False)
        self.assertIn("cannot reach the Claude API", text)

    def test_stopping_mid_reply_keeps_what_was_said(self) -> None:
        stream = _sse(_delta("one "), _delta("two "), _delta("three"), {"type": "message_stop"})
        seen: list[str] = []

        def emit(event: Event) -> None:
            if event.event == "delta":
                seen.append(event.text)

        with mock.patch.object(claude.ClaudeProvider, "_open", staticmethod(lambda *a, **k: stream)):
            text = self._provider().respond("hi", [], emit=emit, should_stop=lambda: bool(seen))
        self.assertEqual(text, "one ")
        self.assertEqual(seen, ["one "])


class TestConversationShape(unittest.TestCase):
    def test_the_first_message_is_always_the_user_and_roles_alternate(self) -> None:
        history = [
            {"role": "assistant", "content": "stale"},
            {"role": "user", "content": "first"},
            {"role": "user", "content": "again"},
            {"role": "assistant", "content": "reply"},
        ]
        turns = claude._messages(history, "now")
        self.assertEqual(turns[0]["role"], "user")
        roles = [t["role"] for t in turns]
        for a, b in zip(roles, roles[1:]):
            self.assertNotEqual(a, b)
        self.assertEqual(turns[-1], {"role": "user", "content": "now"})

    def test_a_reply_without_history_is_just_the_question(self) -> None:
        self.assertEqual(claude._messages([], "hi"), [{"role": "user", "content": "hi"}])


class TestRegistration(unittest.TestCase):
    def test_claude_is_registered_but_never_chosen_automatically(self) -> None:
        self.assertIn("claude", providers.registry())
        settings = _settings(allow=True, provider="auto")
        with mock.patch.object(claude.ClaudeProvider, "available", return_value=True):
            chosen, _reason = providers.select(settings)
        self.assertNotIsInstance(chosen, claude.ClaudeProvider)

    def test_the_provider_setting_accepts_claude(self) -> None:
        from halcyon import settings as settings_module

        self.assertIn("claude", settings_module.choices_for("assistant.provider"))

    def test_the_default_keeps_cloud_models_off(self) -> None:
        from halcyon import settings as settings_module

        defaults = settings_module.defaults()
        self.assertFalse(defaults["assistant"]["privacy"]["allowCloudModels"])


if __name__ == "__main__":
    unittest.main()
