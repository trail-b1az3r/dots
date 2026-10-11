"""The Claude API backend: the Anthropic Messages API, with an API key.

This is the one backend that sends what you say to a company's servers, so
it is held to stricter rules than the others:

* It is never chosen automatically. Only `assistant.provider = "claude"`
  selects it.
* It refuses to run until `assistant.privacy.allowCloudModels` is true.
  That switch is off by default and is shown in Settings with what it
  means.
* The key comes from `ANTHROPIC_API_KEY` or from a file only this user can
  read. It is never written to the log, the settings file, or any error.
* Command intents are still handled on this machine first. A sentence such
  as "turn the volume down" is never sent anywhere.

What this backend does not do is sign in with a claude.ai subscription.
Subscriptions and API access are separate products, and there is no public
sign-in that lets a desktop tool use a subscription on the user's behalf,
so no login flow is offered for one.
"""

from __future__ import annotations

import json
import os
import stat
import urllib.error
import urllib.request
from typing import Any, Callable, Optional

from ... import paths
from .. import intents as intents_module
from ..protocol import Event
from . import Provider

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
ENV_KEY = "ANTHROPIC_API_KEY"
KEY_FILE = paths.CONFIG_DIR / "secrets" / "anthropic.key"

#: Used when settings name no model. Chosen to match the default most
#: users will want: capable, and quick enough for a conversation.
DEFAULT_MODEL = "claude-sonnet-5-5"

SYSTEM_PROMPT = (
    "You are Halcyon, the assistant built into this Linux desktop. "
    "Answer briefly and plainly. Replies are often read aloud, so keep them "
    "to a few sentences unless asked for detail. You cannot control the "
    "desktop from here; if the user asks you to do something, say what "
    "command would do it. If you do not know something, say so."
)


# ── Key handling ───────────────────────────────────────────────────────


def _key_file_mode_ok(path: os.PathLike[str] | str) -> bool:
    """A key file that anyone else on the machine can read is not one we use."""
    try:
        mode = os.stat(path).st_mode
    except OSError:
        return False
    return not mode & (stat.S_IRWXG | stat.S_IRWXO)


def read_key(env: Optional[dict[str, str]] = None) -> tuple[Optional[str], str]:
    """`(key, source)`, where source says where it came from or why none.

    The key itself is returned to the caller and to nothing else.
    """
    environ = os.environ if env is None else env
    from_env = environ.get(ENV_KEY, "").strip()
    if from_env:
        return from_env, "environment"
    try:
        if KEY_FILE.is_file():
            if not _key_file_mode_ok(KEY_FILE):
                return None, f"{KEY_FILE} is readable by other users; run chmod 600"
            text = KEY_FILE.read_text(encoding="utf-8").strip()
            if text:
                return text, "key file"
    except OSError as exc:
        return None, f"cannot read {KEY_FILE}: {exc.strerror or exc}"
    return None, "no key set"


def store_key(key: str) -> None:
    """Write the key to the key file with owner-only permissions."""
    key = key.strip()
    if not key:
        raise ValueError("the key is empty")
    if any(ch.isspace() for ch in key):
        raise ValueError("the key contains spaces or line breaks")
    KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(KEY_FILE.parent, 0o700)
    fd = os.open(KEY_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(key + "\n")
    os.chmod(KEY_FILE, 0o600)


def forget_key() -> bool:
    try:
        KEY_FILE.unlink()
        return True
    except FileNotFoundError:
        return False


# ── The provider ───────────────────────────────────────────────────────


def _claude_settings(settings: dict[str, Any]) -> dict[str, Any]:
    return settings.get("assistant", {}).get("claude", {}) or {}


def _allowed(settings: dict[str, Any]) -> bool:
    privacy = settings.get("assistant", {}).get("privacy", {}) or {}
    return bool(privacy.get("allowCloudModels", False))


class ClaudeProvider(Provider):
    id = "claude"
    title = "Claude API"

    #: Overridable for tests; the real call goes through urllib.
    _open: Callable[..., Any] = staticmethod(urllib.request.urlopen)  # type: ignore[assignment]

    def __init__(self, settings: dict[str, Any], *, env: Optional[dict[str, str]] = None):
        super().__init__(settings)
        self._env = env

    # ── availability ───────────────────────────────────────────────────

    def model(self) -> str:
        return str(_claude_settings(self.settings).get("model") or DEFAULT_MODEL)

    def max_tokens(self) -> int:
        return int(_claude_settings(self.settings).get("maxTokens", 1024))

    def available(self) -> bool:
        return self.health()[0]

    def health(self) -> tuple[bool, str]:
        if not _allowed(self.settings):
            return False, (
                "sending questions to Claude is off; turn on "
                "Settings → Privacy → Allow cloud models"
            )
        key, source = read_key(self._env)
        if key is None:
            return False, f"no API key ({source}); run `halcyon assistant claude key set`"
        return True, f"model {self.model()}, key from {source}"

    # ── answering ──────────────────────────────────────────────────────

    def respond(self, prompt, history, *, emit, should_stop) -> str:
        prompt = (prompt or "").strip()
        if not prompt:
            return ""

        # Commands never leave the machine. The local provider owns the
        # intent handling, so reuse it rather than copying it.
        intent = intents_module.parse(prompt)
        if intent is not None:
            from .local import LocalProvider

            return LocalProvider(self.settings)._run_intent(intent, emit=emit)

        ok, status = self.health()
        if not ok:
            emit(Event("error", text=status))
            return status

        emit(Event("state", state="thinking"))
        messages = _messages(history, prompt)
        try:
            return self._stream(messages, emit=emit, should_stop=should_stop)
        except ClaudeError as exc:
            message = str(exc)
            emit(Event("error", text=message))
            return message

    def _stream(self, messages, *, emit, should_stop) -> str:
        key, _source = read_key(self._env)
        if key is None:  # pragma: no cover - health() ran just before this
            raise ClaudeError("no API key")
        body = {
            "model": self.model(),
            "max_tokens": self.max_tokens(),
            "system": SYSTEM_PROMPT,
            "messages": messages,
            "stream": True,
        }
        request = urllib.request.Request(  # noqa: S310 - fixed HTTPS endpoint
            API_URL,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "content-type": "application/json",
                "x-api-key": key,
                "anthropic-version": API_VERSION,
            },
            method="POST",
        )
        try:
            response = self._open(request, timeout=60)
        except urllib.error.HTTPError as exc:
            raise ClaudeError(_http_message(exc.code, exc.read(2048))) from None
        except (urllib.error.URLError, OSError) as exc:
            raise ClaudeError(f"cannot reach the Claude API: {exc.__class__.__name__}") from None

        collected: list[str] = []
        try:
            with response:
                for raw in response:
                    if should_stop():
                        emit(Event("state", state="idle"))
                        break
                    line = raw.decode("utf-8", errors="replace").strip()
                    if not line.startswith("data:"):
                        continue
                    event = _parse_event(line[len("data:") :].strip())
                    if event is None:
                        continue
                    if event["type"] == "error":
                        raise ClaudeError(f"the Claude API reported an error: {event.get('error', {}).get('type', 'unknown')}")
                    if event["type"] == "content_block_delta":
                        delta = event.get("delta", {})
                        if delta.get("type") == "text_delta":
                            text = delta.get("text", "")
                            collected.append(text)
                            emit(Event("delta", text=text))
                    if event["type"] == "message_stop":
                        break
        except OSError as exc:
            raise ClaudeError(f"the connection to Claude broke: {exc.__class__.__name__}") from None
        return "".join(collected)


class ClaudeError(RuntimeError):
    """The API could not answer. The message is safe to show, and holds no key."""


def _http_message(code: int, body: bytes) -> str:
    if code == 401:
        return "Claude rejected the API key (401). Check it with `halcyon assistant claude key status`."
    if code == 403:
        return "Claude refused this request (403). The key may lack access to the model."
    if code == 404:
        return "Claude does not know this model (404). Check Settings → AI Assistant → Model."
    if code == 429:
        return "Claude is rate limiting this key (429). Try again shortly."
    if code >= 500 or code == 529:
        return f"Claude is unavailable right now ({code}). Try again shortly."
    detail = body.decode("utf-8", errors="replace")
    try:
        detail = json.loads(detail).get("error", {}).get("message", "")
    except (ValueError, AttributeError):
        detail = ""
    return f"Claude returned {code}" + (f": {detail[:200]}" if detail else ".")


def _parse_event(payload: str) -> Optional[dict[str, Any]]:
    if not payload or payload == "[DONE]":
        return None
    try:
        data = json.loads(payload)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _messages(history: list[dict[str, str]], prompt: str) -> list[dict[str, str]]:
    """The conversation in the shape the Messages API requires: user first,
    roles alternating, and nothing but text."""
    turns: list[dict[str, str]] = []
    for item in history[-12:]:
        role = item.get("role")
        text = str(item.get("content", "")).strip()
        if role not in ("user", "assistant") or not text:
            continue
        if turns and turns[-1]["role"] == role:
            turns[-1]["content"] += "\n" + text
        else:
            turns.append({"role": role, "content": text})
    while turns and turns[0]["role"] != "user":
        turns.pop(0)
    if turns and turns[-1]["role"] == "user":
        turns[-1]["content"] += "\n" + prompt
    else:
        turns.append({"role": "user", "content": prompt})
    return turns
